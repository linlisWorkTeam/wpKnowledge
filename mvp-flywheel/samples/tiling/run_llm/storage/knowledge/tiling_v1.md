# tiling 模块知识

> 来源：/root/projects/wpKnowledge/mvp-flywheel/samples/tiling/src/add_custom_tiling.cpp（sources: /root/projects/wpKnowledge/mvp-flywheel/samples/tiling/src/add_custom_tiling.cpp）

## 函数 compute_tiling

```c
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
```

- 为什么：compute_tiling 的实现逻辑见上方代码摘录（MVP 桩直接引用源码行为）
- 溯源：/root/projects/wpKnowledge/mvp-flywheel/samples/tiling/src/add_custom_tiling.cpp

