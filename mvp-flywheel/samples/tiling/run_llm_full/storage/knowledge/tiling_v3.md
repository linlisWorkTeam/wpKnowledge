# Tiling 计算模块解释型知识文档

## 模块概述

本模块负责 Host 侧 Tiling 参数计算。其核心目标是根据总数据长度 `totalLength` 和可用计算核心数 `availableCoreNum`，推算出核函数运行所需的切分参数（实际分块数、每块数据量、尾核数据量），从而指导 AI Core 侧的循环搬运与并行计算。

## 常量与数据结构

- `TILE_LENGTH = 1024`：单次搬运/处理的数据元素数，是数据切分的基本粒度，所有计算均围绕 tile 数展开。
- `DOUBLE_BUFFER = 2`：表示双缓冲深度。该常量在 Tiling 计算中不直接参与运算，通常用于核函数内部缓冲配置。
- `AddTilingData`：Tiling 参数结构体，包含以下字段：
  - `totalLength`：输入总长度，原样透传给核函数。
  - `blockNum`：实际参与数据切分的“任务块/核”数量。
  - `numPerCore`：除最后一个块外，每个块处理的数据量。
  - `tailNumLastCore`：最后一个块实际处理的数据量。

## 函数签名

```cpp
AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum);
```

## 输入参数语义

| 参数 | 类型 | 语义 |
|------|------|------|
| `totalLength` | `uint32_t` | 待处理的数据元素总数，必须为非负值。 |
| `availableCoreNum` | `uint32_t` | 可用计算核心数。若传入 `0`，视为无效输入，模块内部按 `1` 处理以避免除零。 |

## 输出字段语义

- `totalLength`：透传输入参数，供核函数校验实际数据量。
- `blockNum`：实际需要的任务块/核心数。该值由数据总量反推得出，**不一定等于** `availableCoreNum`。当数据量较小时，`blockNum` 可能小于可用核心数，表示部分核无需参与计算。
- `numPerCore`：前 `blockNum - 1` 个任务块各自处理的数据量。该值始终是 `TILE_LENGTH` 的整数倍，可视为一个“满块”的数据量。
- `tailNumLastCore`：最后一个任务块处理的数据量。正常输入下满足 `0 < tailNumLastCore <= numPerCore`，当总长度恰好被整除时，它等于 `numPerCore`。

## 算法步骤（伪代码描述）

算法的核心思想是“先按 tile 粒度粗分，再按核心均分，最后一轮补齐”。

```
输入：totalLength, availableCoreNum
输出：AddTilingData

若 availableCoreNum == 0，则 actualCores = 1；否则 actualCores = availableCoreNum

1. 计算总 tile 数：
   totalTiles = ceil(totalLength / TILE_LENGTH)
   // 整数实现： (totalLength + TILE_LENGTH - 1) / TILE_LENGTH

2. 计算每个核心平均应分得的 tile 数：
   tilesPerCore = ceil(totalTiles / actualCores)
   // 整数实现： (totalTiles + actualCores - 1) / actualCores

3. 计算实际需要的任务块数：
   blockNum = ceil(totalTiles / tilesPerCore)
   // 整数实现： (totalTiles + tilesPerCore - 1) / tilesPerCore

4. 计算每满块的数据量：
   numPerCore = tilesPerCore * TILE_LENGTH

5. 计算最后一个任务块的数据量：
   tailNumLastCore = totalLength - numPerCore * (blockNum - 1)

6. 组合返回 AddTilingData{totalLength, blockNum, numPerCore, tailNumLastCore}
```

说明：
- 步骤 1～3 均采用“向上取整”除法，目的是保证所有数据都能被覆盖。
- 步骤 3 中利用 `tilesPerCore` 反推 `blockNum`，其效果是：当核心数充足时，`blockNum` 可能小于 `availableCoreNum`；当核心数紧张时，`blockNum` 等于 `availableCoreNum` 或略大（实际上不会大于，因为 `tilesPerCore` 是向上取整的结果，`blockNum = ceil(totalTiles / tilesPerCore)` 必然 ≤ `actualCores`）。
- 步骤 5 中，由于 `blockNum` 是向上取整得到的最小整数，前 `blockNum-1` 个块合计数据量一定小于 `totalLength`，因此 `tailNumLastCore` 始终为正（在 `totalLength > 0` 且无溢出的前提下）。

## 边界条件与特殊处理

### 1. `availableCoreNum == 0`

显式处理为 `actualCores = 1`，避免 `tilesPerCore` 计算时出现整数除零。

### 2. `totalLength` 很小（例如小于 `TILE_LENGTH`）

- `totalTiles = 1`。
- 若 `actualCores > 1`，则 `tilesPerCore = 1`，`blockNum = 1`。
- 此时只产生一个任务块，`numPerCore = TILE_LENGTH`，`tailNumLastCore = totalLength`。
- 语义正确，但意味着只使用 1 个核心。

### 3. `totalLength == 0`（缺陷）

- `totalTiles = 0`，继而 `tilesPerCore = 0`。
- 计算 `blockNum` 时需要执行 `totalTiles / tilesPerCore`，除数为 0，产生未定义行为。
- **这是已知边界缺陷**。调用方应禁止传入 `totalLength == 0`，或实现需增加保护逻辑（例如直接返回 `blockNum = 0` 的 Tiling 数据）。

### 4. 大数乘法溢出风险（缺陷）

- `numPerCore = tilesPerCore * TILE_LENGTH` 采用 `uint32_t` 乘法。
- 当 `totalLength` 接近 `UINT32_MAX`（约 42.9 亿）且 `availableCoreNum == 1` 时，`tilesPerCore` 约为 `4194304`，`numPerCore = 4194304 * 1024 = 4294967296`，恰好超过 `UINT32_MAX` 发生回绕，得到错误结果。
- 后续 `numPerCore * (blockNum - 1)` 也会进一步放大错误。
- **建议**：中间计算使用 `uint64_t`，或在调用侧限制 `totalLength` 的最大值，确保 `totalLength * (blockNum - 1)` 不溢出。

### 5. `blockNum < availableCoreNum` 的预期行为

当总数据量较小或 `availableCoreNum` 很大时，`blockNum` 会小于 `availableCoreNum`。这意味着并非所有传入的核都会被使用。核函数侧应根据 `blockNum`（而非 `availableCoreNum`）进行任务调度，否则可能导致多余核读取越界或空转。

### 6. `tailNumLastCore` 的取值范围

在无溢出且 `totalLength > 0` 时，由于 `(blockNum - 1) * tilesPerCore < totalTiles`，可以推出：

- `tailNumLastCore > 0`
- `tailNumLastCore <= numPerCore`

因此最后一个核不会出现“零数据”任务；当总长度恰好被整块切分时，尾核数据量等于 `numPerCore`。

## 已知缺陷汇总与修复建议

| 缺陷 | 风险等级 | 触发条件 | 建议 |
|------|----------|----------|------|
| `totalLength == 0` 时除零 | 高 | 任何调用 | 增加前置判断：若 `totalLength == 0`，返回全零 Tiling 或由调用方拦截 |
| `uint32_t` 乘法溢出 | 中高 | `totalLength` 接近 `UINT32_MAX` 且 `availableCoreNum` 较小 | 使用 `uint64_t` 作为中间类型，或限制业务数据量上限 |
| 未显式说明 `blockNum` 可能小于 `availableCoreNum` | 低 | 正常场景 | 在接口文档中明确该语义，核函数按 `blockNum` 绑定任务 |

## 溯源

- 接口头文件：`add_custom_tiling.h`（常量、`AddTilingData` 结构体、`compute_tiling` 声明）
- 算法逻辑来源：cannbot `add_custom` 模板 `main.cpp` 中的 Tiling 计算部分（本文档仅描述逻辑，未包含实现源码）
## 修订补丁 tiling-field-assignment-1

- 判据：8个tiling测试全部通过（tiling-default、tiling-multicore-2、tiling-multicore-8、tiling-exact-1、tiling-exact-2、tiling-small、tiling-big、tiling-zero-core）
- 详情：检查compute_tiling中构造AddTilingData的代码，确保返回的blockNum是算法计算出的实际任务块数、numPerCore是每块数据量、tailNumLastCore是最后一个块的实际数据量，且tailNumLastCore不为0（除非totalLength为0的边界）。具体做法：使用结构体列表初始化，按声明顺序返回{totalLength, blockNum, numPerCore, tailNumLastCore}，或显式逐字段赋值；不要将numPerCore赋给blockNum，不要将tailNumLastCore赋给numPerCore，也不要将tailNumLastCore硬编码为0。若有中间变量命名相似，请重命名以区分。

## 修订补丁 tiling-field-assignment-1

- 判据：8 个 tiling 测试全部通过；所有 totalLength>0 用例的 tailNumLastCore 均大于 0，且 blockNum 与 numPerCore 不再相等
- 详情：检查 compute_tiling 中返回 AddTilingData 的代码，确保按算法步骤依次计算 totalTiles、tilesPerCore、blockNum、numPerCore、tailNumLastCore，并使用结构体列表初始化按声明顺序返回 {totalLength, blockNum, numPerCore, tailNumLastCore}。严禁将 numPerCore 赋给 blockNum，严禁将 tailNumLastCore 硬编码为 0。若代码中使用了与算法中间变量同名的局部变量（如 totalTiles、tilesPerCore），请确认变量含义，必要时重命名避免混淆。

## 修订补丁 tiling-zero-boundary

- 判据：tiling-zero-core 用例通过；totalLength==0 时不会发生除零或未定义行为
- 详情：在 compute_tiling 入口增加对 totalLength==0 的保护：若为 0，应返回 blockNum=0、numPerCore=0、tailNumLastCore=0 的 AddTilingData，或直接返回全零结构体，避免后续除法除零。
