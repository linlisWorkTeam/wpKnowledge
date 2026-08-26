#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum) {
    uint32_t cores = (availableCoreNum == 0) ? 1u : availableCoreNum;

    uint64_t totalTiles = (static_cast<uint64_t>(totalLength) + TILE_LENGTH - 1) / TILE_LENGTH;
    uint64_t tilesPerCore = (totalTiles + cores - 1) / cores;
    uint64_t blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;

    uint32_t blockNum32 = static_cast<uint32_t>(blockNum);
    uint32_t numPerCore = totalLength / blockNum32;
    uint32_t tailNumLastCore = totalLength % numPerCore;

    return {totalLength, blockNum32, numPerCore, tailNumLastCore};
}