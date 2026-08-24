#include "add_custom_tiling.h"

/* compute_tiling: Host 侧 Tiling 计算。
   逻辑来自 cannbot add_custom 模板 main.cpp（真实算子平台业务代码）：
     totalTiles      = ceil(totalLength / TILE_LENGTH)
     tilesPerCore    = ceil(totalTiles / availableCoreNum)
     blockNum        = ceil(totalTiles / tilesPerCore)
     numPerCore      = tilesPerCore * TILE_LENGTH
     tailNumLastCore = totalLength - numPerCore * (blockNum - 1)
   边界语义：
     - availableCoreNum 为 0 时按 1 处理（避免除零）
     - tailNumLastCore 为最后一个核处理的数据量（可小于 numPerCore） */
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
    tiling.tailNumLastCore = totalLength - tiling.numPerCore * (blockNum - 1);
    return tiling;
}
