#include "add_custom_tiling.h"
AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum)
{
    AddTilingData tiling;
    tiling.totalLength = totalLength;

    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;
    uint32_t totalTiles = (totalLength + TILE_LENGTH - 1) / TILE_LENGTH;
    uint32_t tilesPerCore = (totalTiles + cores - 1) / cores;
    uint32_t blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;

    tiling.blockNum = blockNum;
    tiling.numPerCore = tilesPerCore * TILE_LENGTH;
    
    return tiling;
}