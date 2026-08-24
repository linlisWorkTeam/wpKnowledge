#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum)
{
    AddTilingData tiling{};
    tiling.totalLength = totalLength;

    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;

    uint32_t totalTiles = totalLength / TILE_LENGTH;
    if (totalLength % TILE_LENGTH != 0) {
        ++totalTiles;
    }

    if (totalTiles == 0) {
        tiling.blockNum = 0;
        tiling.numPerCore = 0;
        tiling.tailNumLastCore = 0;
        return tiling;
    }

    uint32_t tilesPerCore = totalTiles / cores;
    if (totalTiles % cores != 0) {
        ++tilesPerCore;
    }

    uint32_t blockNum = totalTiles / tilesPerCore;
    if (totalTiles % tilesPerCore != 0) {
        ++blockNum;
    }

    tiling.blockNum = blockNum;

    uint64_t numPerCore64 = static_cast<uint64_t>(tilesPerCore) * TILE_LENGTH;
    tiling.numPerCore = static_cast<uint32_t>(numPerCore64);

    uint64_t processedBeforeLast = static_cast<uint64_t>(blockNum - 1) * numPerCore64;
    uint64_t tailNum = static_cast<uint64_t>(totalLength) - processedBeforeLast;
    tiling.tailNumLastCore = static_cast<uint32_t>(tailNum);

    return tiling;
}