/* 原生测试文件示例（模拟用户本地测试集形态）。
   用户本地测试集 = 直接可编译的 C 测试驱动，含 main，逐用例断言，
   运行后打印 "PASS n/total"（与 JSON 模式同约定）。
   用法：demo.py --evalset samples/evalset_native */
#include <stdio.h>
#include <math.h>
#include "calc.h"

static int _eq_double(double a, double b) { return fabs(a - b) < 1e-9; }

int main(void)
{
    int passed = 0, total = 0;

    total++; if (add(2, 3) == 5) passed++;
    total++; if (add(-5, 5) == 0) passed++;
    total++; if (clamp(15, 0, 10) == 10) passed++;
    total++; if (clamp(-3, 0, 10) == 0) passed++;
    total++; if (clamp(5, 0, 10) == 5) passed++;
    total++; if (max3(1, 2, 3) == 3) passed++;
    total++; if (max3(3, 2, 1) == 3) passed++;
    total++; if (_eq_double(mean(1, 3), 2.0)) passed++;
    total++; if (_eq_double(mean(0, 5), 2.5)) passed++;

    printf("PASS %d/%d\n", passed, total);
    return total - passed;
}
