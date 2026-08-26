#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum) {
    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;

    uint32_t totalTiles = totalLength / TILE_LENGTH + ((totalLength % TILE_LENGTH) != 0);

    AddTilingData tiling{0, 0, 0, 0};
    if (totalTiles == 0) {
        return tiling;
    }

    uint32_t tilesPerCore = totalTiles / cores + ((totalTiles % cores) != 0);
    uint32_t blockNum = totalTiles / tilesPerCore + ((totalTiles % tilesPerCore) != 0);
    uint32_t numPerCore = tilesPerCore * TILE_LENGTH;
    uint32_t tailNumLastCore = totalLength - (blockNum - 1) * numPerCore;

    tiling.totalLength = totalLength;
    tiling.blockNum = blockNum;
    tiling.numPerCore = numPerCore;
    tiling.tailNumLastCore = tailNumLastCore;

    return tiling;
}