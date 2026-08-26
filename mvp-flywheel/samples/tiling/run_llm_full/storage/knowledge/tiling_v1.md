# AddCustom Tiling 模块解释型知识文档

## 溯源

- 接口头文件：`add_custom_tiling.h`
- 实现参考：`cannbot add_custom` 模板 `main.cpp` 中的 Host 侧 Tiling 计算逻辑
- 模块作用：为 `add_custom` 算子核函数生成运行时 Tiling 参数，指导核函数按 Tile 分块、按核分配数据量。

---

## 1. 模块概述

本模块定义了一个 Tiling 数据结构 `AddTilingData`，并实现了 Host 侧 Tiling 计算函数 `compute_tiling`。其核心目标是将 `totalLength` 个元素的加法任务切分为若干块（Tile），并将这些块均匀或近似均匀地分配到多个计算核心上执行，同时通过常量参数控制单次搬运/处理的数据量，以优化 UB（Unified Buffer）内存占用。

---

## 2. 常量定义

| 常量名 | 类型 | 值 | 语义 |
|--------|------|-----|------|
| `TILE_LENGTH` | `uint32_t` | `1024` | 单次搬运/处理的数据元素数量。UB 内存占用与该值相关，是 Tiling 的基本粒度。 |
| `DOUBLE_BUFFER` | `int32_t` | `2` | 双缓冲系数。当前模块中未直接使用，但影响核侧缓冲配置的预留语义。 |

> 说明：`DOUBLE_BUFFER` 在本 Tiling 计算中未参与公式，但它是核函数侧配置双缓冲的常数，保留在头文件中用于后续内存分配或流水线设计。

---

## 3. 数据结构：`AddTilingData`

| 字段 | 类型 | 语义 |
|------|------|------|
| `totalLength` | `uint32_t` | 输入数据总长度（元素个数），由 Host 传入，透传给核函数。 |
| `blockNum` | `uint32_t` | 实际需要启动的核块（block）数量。 |
| `numPerCore` | `uint32_t` | 每个核心处理的标准数据量（元素个数），固定为 `tilesPerCore * TILE_LENGTH`，通常为 TILE_LENGTH 的整数倍。 |
| `tailNumLastCore` | `uint32_t` | 最后一个核心实际需要处理的数据量（元素个数）。通常小于等于 `numPerCore`，用于处理无法整除的余量部分。 |

---

## 4. 函数签名与职责

### `compute_tiling`

```cpp
AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum);
```

**职责**：根据用户指定的总数据长度和可用核数，计算核函数所需的 Tiling 参数，返回填充完整的 `AddTilingData` 结构体。

---

## 5. 输入参数语义

| 参数 | 类型 | 语义 | 约束/异常情况 |
|------|------|------|---------------|
| `totalLength` | `uint32_t` | 待处理数据的总元素个数。 | 若为 0，计算结果 `totalTiles=0`，`tilesPerCore` 可能为 0，`blockNum` 计算时需注意除以 0 风险（见缺陷分析）。 |
| `availableCoreNum` | `uint32_t` | 当前可用的计算核心数量。 | 若为 0，模块内部将其视为 1，避免除零错误；若大于实际硬件核数，调用方需自行保证合理性。 |

---

## 6. 输出字段语义（返回的 `AddTilingData`）

- `totalLength`：等于输入 `totalLength`，原样透传。
- `blockNum`：计算出的任务分块数量，表示需要多少个核块来执行全部数据。
- `numPerCore`：除了最后一个核块外，每个核块的标准数据量。
- `tailNumLastCore`：最后一个核块实际分配的数据量，用于处理 `totalLength` 不能被 `numPerCore` 整除的情况。

---

## 7. 算法步骤（伪代码描述）

```text
function compute_tiling(totalLength, availableCoreNum):
    cores = (availableCoreNum == 0) ? 1 : availableCoreNum

    totalTiles = ceil(totalLength / TILE_LENGTH)
    // 即 (totalLength + TILE_LENGTH - 1) / TILE_LENGTH

    tilesPerCore = ceil(totalTiles / cores)
    // 每个核心承担的最小完整 tile 数量

    blockNum = ceil(totalTiles / tilesPerCore)
    // 实际需要的 block 数量，通常等于 cores，但当 totalTiles 小于 cores 时可能小于 cores

    numPerCore = tilesPerCore * TILE_LENGTH

    tailNumLastCore = totalLength - numPerCore * (blockNum - 1)
    // 最后一个 core 的余量数据量

    return AddTilingData { totalLength, blockNum, numPerCore, tailNumLastCore }
```

**逐步解释**：

1. 输入校验：将 `availableCoreNum == 0` 归一化为 1，防止除零。
2. 将总长度按 `TILE_LENGTH` 向上取整得到总 tile 数 `totalTiles`。
3. 将总 tile 数尽量均分到每个核心，得到 `tilesPerCore`。
4. 根据 `tilesPerCore` 反推实际需要多少个 block（`blockNum`）。
5. 每个核心的标准数据量 `numPerCore` 为 `tilesPerCore * TILE_LENGTH`。
6. 最后一个核心的数据量 `tailNumLastCore` 为总长度减去前面所有核心（除最后一个外）处理的数据量之和。
   - 当 `totalLength` 能被 `numPerCore` 整除时，`tailNumLastCore` 等于 `numPerCore`；
   - 否则 `tailNumLastCore` 为余数（小于 `numPerCore`）。

---

## 8. 边界条件与特殊处理

| 场景 | 处理方式 | 结果 |
|------|----------|------|
| `availableCoreNum = 0` | 视为 `cores = 1` | 避免除零，但实际单核执行，可能导致性能下降。 |
| `totalLength = 0` | 不做特殊拦截 | `totalTiles = 0`；`tilesPerCore = ceil(0 / cores) = 0`；`blockNum = ceil(0 / 0)` —— 出现除零风险（见缺陷）。 |
| `totalLength < TILE_LENGTH` | `totalTiles = 1`，`tilesPerCore = 1`，`blockNum = 1` | 单块执行，`numPerCore = TILE_LENGTH`，`tailNumLastCore = totalLength`。 |
| `totalLength` 恰好被 `TILE_LENGTH` 整除 | `totalTiles` 为整数 | 所有 core 的 `tailNumLastCore` 均等于 `numPerCore`。 |
| `totalTiles` 不足以填满所有核心 | `blockNum` 可能小于 `cores` | 实际启动的核数少于可用核数，属于资源利用不充分，但逻辑正确。 |
| `tailNumLastCore` 可能为 0 | 当 `totalLength = numPerCore * (blockNum - 1)` 时 | 最后一个核被分配 0 个元素，核函数需能处理空任务或调用方避免该情形。 |

---

## 9. 潜在缺陷与风险标注

> ⚠️ **缺陷 1：`totalLength = 0` 时除零风险**
>
> 若 `totalLength = 0`，则 `totalTiles = 0`，`tilesPerCore = (0 + cores - 1) / cores = 0`，随后计算 `blockNum` 时执行 `(0 + 0 - 1) / 0`，即除数为 0，导致未定义行为或崩溃。建议在函数入口增加 `totalLength == 0` 的边界处理，或保证调用方不会传入 0。

> ⚠️ **缺陷 2：整数溢出风险**
>
> `numPerCore * (blockNum - 1)` 可能超出 `uint32_t` 表示范围，尤其是当 `tilesPerCore` 和 `TILE_LENGTH` 较大时。虽然实际场景中数据长度通常受限，但严格起见应使用 `uint64_t` 中间变量或进行溢出校验。

> ⚠️ **缺陷 3：`tailNumLastCore` 语义可能难以覆盖非均匀分配**
>
> 该算法假设除最后一个 core 外的所有 core 处理相同数据量 `numPerCore`，且最后一个 core 处理余量 `tailNumLastCore`。若 `totalTiles` 与 `cores` 的整除关系导致 `blockNum` 小于 `cores`，则部分核心不会被使用，可能引发负载不均衡。

> ⚠️ **缺陷 4：`availableCoreNum` 与实际硬件核数不匹配**
>
> 若传入的 `cores` 大于硬件实际核心数，`blockNum` 可能大于硬件支持的核数，需要调用方确保 `availableCoreNum` 在合理范围内，否则可能触发硬件调度错误。

---

## 10. 使用建议

- 调用前检查 `totalLength > 0`，或由本函数内部做保护（当前未实现，需改进）。
- 核函数侧应根据 `blockNum` 分配核，每个核根据其 `block_id` 判断是否为最后一个核，以决定使用 `tailNumLastCore` 还是 `numPerCore`。
- 若需双缓冲流水，可结合 `TILE_LENGTH` 和 `DOUBLE_BUFFER` 评估 UB 占用，但本 Tiling 模块不涉及具体内存地址计算。