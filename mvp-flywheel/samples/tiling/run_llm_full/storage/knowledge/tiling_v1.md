# 模块：Tiling 计算（add_custom_tiling）

## 概述

本模块为 `add_custom` 算子提供 Host 侧 Tiling 计算。其核心职责是将输入数据的总长度 `totalLength` 按固定粒度 `TILE_LENGTH` 切分成若干个 tile，再结合可用核数 `availableCoreNum`，推导出需要几个处理块（block）、每个核处理多少数据、以及最后一个核的尾部数据量。计算结果通过 `AddTilingData` 结构体传递给核函数，用于指导 Device 侧的数据搬运与计算循环。

模块中还定义了 `TILE_LENGTH` 和 `DOUBLE_BUFFER` 两个常量，其中 `TILE_LENGTH` 决定基本数据处理粒度，`DOUBLE_BUFFER` 用于后续 UB（Unified Buffer）双缓冲设计。

## 常量定义

| 常量名 | 类型 | 值 | 语义 |
|--------|------|----|------|
| `TILE_LENGTH` | `uint32_t` | `1024` | 单次搬运/处理的数据基本块大小（元素数） |
| `DOUBLE_BUFFER` | `int32_t` | `2` | 双缓冲因子，用于 UB 内存规划 |

## 数据结构：`AddTilingData`

```cpp
struct AddTilingData {
    uint32_t totalLength;      // 输入数据总元素数
    uint32_t blockNum;         // 实际开启的核数 / 循环块数
    uint32_t numPerCore;       // 每个核（除尾核外）处理的最大元素数
    uint32_t tailNumLastCore;  // 最后一个核实际处理的元素数
};
```

### 字段语义

| 字段 | 类型 | 语义 |
|------|------|------|
| `totalLength` | `uint32_t` | 输入数据的总元素数，原样透传。 |
| `blockNum` | `uint32_t` | 总共需要多少个“块”来处理所有 tile。该值通常等于或小于 `availableCoreNum`。 |
| `numPerCore` | `uint32_t` | 每个核（除最后一个核外）负责处理的元素数，等于 `tilesPerCore * TILE_LENGTH`。 |
| `tailNumLastCore` | `uint32_t` | 最后一个核实际负责处理的元素数，可能小于 `numPerCore`。 |

## 函数 `compute_tiling`

### 函数签名

```cpp
AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum);
```

### 职责

根据总数据长度和可用核数，计算 tiling 参数，生成 `AddTilingData` 结构体。

### 输入参数

- `totalLength`：输入数据总元素数，类型 `uint32_t`。允许为 0，但当前实现存在缺陷（见边界缺陷）。
- `availableCoreNum`：硬件可用核数，类型 `uint32_t`。若传入 0，函数内部按 1 处理，避免除零。

### 输出

返回 `AddTilingData` 结构体，字段语义如上所述。

## 算法步骤

1. **确定实际核数**  
   若 `availableCoreNum == 0`，则 `cores = 1`；否则 `cores = availableCoreNum`。

2. **计算总 tile 数**  
   将总长度按 `TILE_LENGTH` 向上取整得到总 tile 数：  
   `totalTiles = ceil(totalLength / TILE_LENGTH)`。

3. **计算每核 tile 数**  
   将总 tile 数按核数向上取整，得到每个核应承担的 tile 数：  
   `tilesPerCore = ceil(totalTiles / cores)`。

4. **计算块数 `blockNum`**  
   用总 tile 数除以每核 tile 数，再向上取整：  
   `blockNum = ceil(totalTiles / tilesPerCore)`。

5. **计算每核元素数**  
   `numPerCore = tilesPerCore * TILE_LENGTH`。

6. **计算尾核数据量**  
   总长度减去前 `blockNum - 1` 个核负责的元素总数：  
   `tailNumLastCore = totalLength - numPerCore * (blockNum - 1)`。

7. 将上述值填入 `AddTilingData` 并返回。

### 伪代码（结构化描述）

```
function compute_tiling(totalLength, availableCoreNum):
    result.totalLength = totalLength
    cores = (availableCoreNum == 0) ? 1 : availableCoreNum
    totalTiles = ceil(totalLength / TILE_LENGTH)
    tilesPerCore = ceil(totalTiles / cores)
    blockNum = ceil(totalTiles / tilesPerCore)
    result.blockNum = blockNum
    result.numPerCore = tilesPerCore * TILE_LENGTH
    result.tailNumLastCore = totalLength - result.numPerCore * (blockNum - 1)
    return result
```

主要数学关系：

- `totalTiles` 表示按 `TILE_LENGTH` 划分出的完整/不完整 tile 总数。
- `tilesPerCore` 对每核应处理的 tile 数向上取整，保证每个核的数据量不低于平均值。
- `blockNum` 不超过 `cores`，当 tile 数不足以填满所有核时，`blockNum < cores`。
- 最后一个核只处理剩余的部分，因此 `tailNumLastCore <= numPerCore`。

## 边界条件与特殊处理

- **`availableCoreNum == 0`**：函数内部将核数强制置为 1，规避除零。
- **`totalLength` 为 `TILE_LENGTH` 的整数倍**：`tailNumLastCore` 将等于 `numPerCore`，所有核处理量一致。
- **`totalLength` 很小**（如 1）：`totalTiles = 1`，`tilesPerCore = 1`，`blockNum = 1`，`numPerCore = TILE_LENGTH`，`tailNumLastCore = 1`，正确。
- **最后一个核的数据量**：由于前 `blockNum-1` 个核处理的 tile 数严格小于总 tile 数，所以 `tailNumLastCore` 必然为正数，不会发生下溢。

## 已知缺陷与风险

> 以下问题存在于当前实现中，使用或修改时需特别关注：

1. **`totalLength == 0` 时除零**  
   若 `totalLength = 0`，则 `totalTiles = 0`，进而 `tilesPerCore = 0`。在计算 `blockNum` 时，分母 `tilesPerCore` 为 0，导致除零崩溃。  
   **建议**：在函数入口处增加 `totalLength == 0` 的显式分支，或调用方保证 `totalLength > 0`。

2. **`totalLength + TILE_LENGTH - 1` 可能发生 uint32_t 回绕**  
   当 `totalLength` 接近 `UINT32_MAX` 时，加上 `TILE_LENGTH - 1` 会导致无符号整数回绕，`totalTiles` 计算错误，进而影响所有下游参数。  
   **建议**：使用 `uint64_t` 进行中间计算，或先判断 `totalLength` 是否超过安全阈值（`UINT32_MAX - TILE_LENGTH + 1`）。

## 使用说明

- 调用方应传入合法的 `totalLength > 0` 和 `availableCoreNum > 0`，并妥善处理上述边界缺陷。
- `DOUBLE_BUFFER` 常量在本函数中未被使用，但在后续核函数内存规划时需结合 `TILE_LENGTH` 使用。
- 返回的 `AddTilingData` 应通过运行时参数传递给核函数，指导每个核上的循环范围和缓冲分配。

## 溯源

- 头文件：`add_custom_tiling.h`
- 实现：`add_custom_tiling.cpp`（逻辑来源于 cannbot add_custom 模板 main.cpp）