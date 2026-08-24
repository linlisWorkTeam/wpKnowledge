#include "calc.h"

/* add: 两数相加 */
int add(int a, int b)
{
    return a + b;
}

/* clamp: 将 x 限制在 [lo, hi] 区间 */
int clamp(int x, int lo, int hi)
{
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

/* max3: 三数取最大 */
int max3(int a, int b, int c)
{
    int m = a;
    if (b > m) m = b;
    if (c > m) m = c;
    return m;
}

/* mean: 两数平均（浮点） */
double mean(double a, double b)
{
    return (a + b) / 2.0;
}
