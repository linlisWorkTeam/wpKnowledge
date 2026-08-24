/* 探针：跑真实源码拿期望输出（《评测集构建指南》附录 C） */
#include <cstdio>
#include "add_custom_tiling.h"

static void show(const char* label, uint32_t totalLength, uint32_t cores)
{
    AddTilingData t = compute_tiling(totalLength, cores);
    std::printf("%s: total=%u cores=%u -> blockNum=%u numPerCore=%u tail=%u\n",
                label, totalLength, cores, t.blockNum, t.numPerCore, t.tailNumLastCore);
}

int main()
{
    /* 模板默认场景 */
    show("default", 8 * 2048, 1);
    /* 多核切分 */
    show("multi-core-2", 8 * 2048, 2);
    show("multi-core-8", 8 * 2048, 8);
    /* 恰好整除 */
    show("exact-tile", 1024, 1);
    show("exact-2tiles", 2048, 1);
    /* 小于单 tile */
    show("small", 100, 1);
    /* 大长度 */
    show("big", 1000000, 4);
    /* 边界：0 核（按 1 处理） */
    show("zero-core", 8 * 2048, 0);
    /* 边界：空长度 */
    show("zero-length", 0, 1);
    return 0;
}
