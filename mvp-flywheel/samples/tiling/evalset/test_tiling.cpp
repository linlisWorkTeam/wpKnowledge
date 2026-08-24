/* 原生测试文件：tiling 模块评测集（模拟用户本地测试集形态）。
   期望输出来自探针程序跑真实源码的结果（红线：禁止编造）。
   运行后打印 PASS n/total。 */
#include <cstdio>
#include "add_custom_tiling.h"

static int _check(const char* id, uint32_t totalLength, uint32_t cores,
                  uint32_t expBlock, uint32_t expNum, uint32_t expTail)
{
    AddTilingData t = compute_tiling(totalLength, cores);
    if (t.blockNum == expBlock && t.numPerCore == expNum && t.tailNumLastCore == expTail) {
        return 1;
    }
    std::printf("FAIL %s: got blockNum=%u numPerCore=%u tail=%u, want %u/%u/%u\n",
                id, t.blockNum, t.numPerCore, t.tailNumLastCore,
                expBlock, expNum, expTail);
    return 0;
}

int main()
{
    int passed = 0, total = 0;

    /* 来自探针真实输出（/tmp/probe2） */
    total++; passed += _check("tiling-default",     8 * 2048, 1, 1, 16384, 16384);
    total++; passed += _check("tiling-multicore-2", 8 * 2048, 2, 2, 8192,  8192);
    total++; passed += _check("tiling-multicore-8", 8 * 2048, 8, 8, 2048,  2048);
    total++; passed += _check("tiling-exact-1",     1024,     1, 1, 1024,  1024);
    total++; passed += _check("tiling-exact-2",     2048,     1, 1, 2048,  2048);
    total++; passed += _check("tiling-small",       100,      1, 1, 1024,  100);
    total++; passed += _check("tiling-big",         1000000,  4, 4, 250880, 247360);
    total++; passed += _check("tiling-zero-core",   8 * 2048, 0, 1, 16384, 16384);

    std::printf("PASS %d/%d\n", passed, total);
    return total - passed;
}
