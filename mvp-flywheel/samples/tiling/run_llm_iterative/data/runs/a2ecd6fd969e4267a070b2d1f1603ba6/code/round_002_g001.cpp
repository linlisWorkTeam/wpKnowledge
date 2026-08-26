#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum) {
    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;

    uint32_t totalTiles = (totalLength + TILE_LENGTH - 1) / TILE_LENGTH;

    if (totalTiles == 0) {
        AddTilingData data;
        data.totalLength = totalLength;
        data.blockNum = 0;
        data.numPerCore = 0;
        data.tailNumLastCore = 0;
        return data;
    }

    uint32_t tilesPerCore = (totalTiles + cores - 1) / cores;
    uint32_t blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;

    uint32_t perCoreAvg = (totalLength + blockNum - 1) / blockNum;
    uint32_t numPerCore = ((perCoreAvg + TILE_LENGTH - 1) / TILE_LENGTH) * TILE_LENGTH;
    uint32_t tailNumLastCore = totalLength - (blockNum - 1) * numPerCore;

    AddTilingData result;
    result.totalLength = totalLength;
    result.blockNum = blockNum;
    result.numPerCore = numPerCore;
    result.tailNumLastCore = tailNumLastCore;
    return result;
}