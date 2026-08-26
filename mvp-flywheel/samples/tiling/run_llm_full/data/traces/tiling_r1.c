#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum) {
    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;

    uint32_t totalTiles = (totalLength + TILE_LENGTH - 1) / TILE_LENGTH;
    uint32_t tilesPerCore = (totalTiles + cores - 1) / cores;
    uint32_t blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;
    uint32_t numPerCore = tilesPerCore * TILE_LENGTH;
    uint32_t tailNumLastCore = totalLength - numPerCore * (blockNum - 1);

    AddTilingData result;
    result.totalLength = totalLength;
    result.blockNum = blockNum;
    result.numPerCore = numPerCore;
    result.tailNumLastCore = tailNumLastCore;
    return result;
}