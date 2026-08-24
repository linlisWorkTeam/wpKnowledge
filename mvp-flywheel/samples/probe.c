/* 探针：跑真实源码拿期望输出（《评测集构建指南》附录 C：期望输出必须来自源码实际行为） */
#include <stdio.h>
#include "calc.h"

int main(void)
{
    printf("add(2,3)=%d\n", add(2, 3));
    printf("add(-5,5)=%d\n", add(-5, 5));
    printf("clamp(15,0,10)=%d\n", clamp(15, 0, 10));
    printf("clamp(-3,0,10)=%d\n", clamp(-3, 0, 10));
    printf("clamp(5,0,10)=%d\n", clamp(5, 0, 10));
    printf("max3(1,2,3)=%d\n", max3(1, 2, 3));
    printf("max3(3,2,1)=%d\n", max3(3, 2, 1));
    printf("max3(2,3,1)=%d\n", max3(2, 3, 1));
    printf("mean(1,3)=%.2f\n", mean(1, 3));
    printf("mean(0,5)=%.2f\n", mean(0, 5));
    return 0;
}
