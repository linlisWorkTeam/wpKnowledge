#include "add_custom_tiling.h"

AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum)
{
    AddTilingData result{};
    result.totalLength = totalLength;

    if (totalLength == 0) {
        result.blockNum = 0;
        result.numPerCore = 0;
        result.tailNumLastCore = 0;
        return result;
    }

    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;

    uint64_t totalTiles64 =
        (static_cast<uint64_t>(totalLength) + TILE_LENGTH - 1) / TILE_LENGTH;
    uint32_t totalTiles = static_cast<uint32_t>(totalTiles64);

    uint32_t tilesPerCore = static_cast<uint32_t>(
        (static_cast<uint64_t>(totalTiles) + cores - 1) / cores);

    result.blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;
    result.numPerCore = static_cast<uint32_t>(
        static_cast<uint64_t>(tilesPerCore) * TILE_LENGTH);
    result.tailNumLastCore = static_cast<uint32_t>(
        static_cast<uint64_t>(totalLength) -
        static_cast<uint64_t>(result.numPerCore) * (result.blockNum - 1));

    return result;
}