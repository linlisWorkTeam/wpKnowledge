#ifndef ADD_CUSTOM_TILING_H
#define ADD_CUSTOM_TILING_H

#include <cstdint>

constexpr uint32_t TILE_LENGTH = 1024;
constexpr int32_t DOUBLE_BUFFER = 2;

struct AddTilingData {
    uint32_t totalLength;
    uint32_t blockNum;
    uint32_t numPerCore;
    uint32_t tailNumLastCore;
};

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum);

#endif
