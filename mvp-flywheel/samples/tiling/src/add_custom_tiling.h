#ifndef ADD_CUSTOM_TILING_H
#define ADD_CUSTOM_TILING_H

#include <cstdint>

/* [CONFIG] 单次搬运/处理的数据量（元素数），影响 UB 内存占用 */
constexpr uint32_t TILE_LENGTH = 1024;
constexpr int32_t  DOUBLE_BUFFER = 2;

/* Tiling 数据结构：向核函数传递的运行时参数 */
struct AddTilingData {
    uint32_t totalLength;
    uint32_t blockNum;
    uint32_t numPerCore;
    uint32_t tailNumLastCore;
};

/* compute_tiling: Host 侧 Tiling 计算（来自 cannbot add_custom 模板 main.cpp） */
AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum);

#endif // ADD_CUSTOM_TILING_H
