#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum) {
    if (totalLength == 0) {
        return AddTilingData{0, 0, 0, 0};
    }

    uint64_t actualCores = (availableCoreNum == 0) ? 1ULL : static_cast<uint64_t>(availableCoreNum);

    uint64_t totalTiles = (static_cast<uint64_t>(totalLength) + TILE_LENGTH - 1) / TILE_LENGTH;
    uint64_t tilesPerCore = (totalTiles + actualCores - 1) / actualCores;
    uint64_t blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;
    uint64_t numPerCore = tilesPerCore * TILE_LENGTH;
    uint64_t tailNumLastCore = static_cast<uint64_t>(totalLength) - numPerCore * (blockNum - 1);

    return AddTilingData{
        static_cast<uint32_t>(blockNum),
        static_cast<uint32_t>(numPerCore),
        static_cast<uint32_t>(tailNumLastCore)
    };
}