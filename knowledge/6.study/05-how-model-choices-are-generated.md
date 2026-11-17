# 05｜从零写 Agent · Chat Completions 的 choices 是怎么生成的？

[上一篇](./04-reading-llm-api-responses.md)从 `choices[0].message.content` 读出了回答。为什么这里用了一个数组？答案要分两层看：**模型在每一步给下一枚 token 打分，推理服务可以用同一份上下文生成一条或多条完整续写。** `choices` 装的是这些完整续写。

## 先看一条回答是怎么生成的

以常见的自回归语言模型为例。输入被转成 token 之后，模型为下一个位置上的候选 token 打分。推理引擎按解码策略选出一个，把它接到已有序列，再继续下一步。

比如给模型一个句子开头「单元测试主要用来」，下一步可能往「验证」这个方向接，也可能往「检查」这个方向接。下面用词来示意，实际计算按 token 进行。

- **贪心解码（greedy decoding）**每一步取当前得分最高的 token。
- **采样（sampling）**按调整后的概率抽取 token。`temperature` 可以改变概率分布的集中程度，`top_p` 可以限制采样范围。

一旦某一步选出的 token 不同，后面的输入序列也就不同了。这个差异可以让同一个问题得到两种措辞，甚至走向两种解法。  
[Hugging Face · Generation with LLMs](https://huggingface.co/docs/transformers/v4.33.0/en/llm_tutorial) · [vLLM · SamplingParams](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)

## n=2 时，服务怎么返回两条回答？

以我们前面用的 vLLM 兼容端点为例，可以在请求里加上 `n: 2`，要求服务基于同一个输入生成两个候选。下面是发给 `POST /v1/chat/completions` 的示例请求体：

```json
{
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "messages": [
    {"role": "user", "content": "用一句话解释什么是单元测试。"}
  ],
  "n": 2,
  "temperature": 0.8,
  "max_tokens": 80
}
```

可以把服务里的工作想成两条生成序列，每条都从同一份输入开始，各自维护已生成的 token 并继续解码。vLLM 的一种具体实现是由 `ParentRequest` 跟踪原请求，把它拆成多个各自只生成一条结果的子请求，然后汇总输出。调用方仍然只发了一次 HTTP 请求。下面是一个省略了无关字段的示意响应：

```json
{
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "单元测试验证一个小的代码单元能否按预期工作。"},
      "finish_reason": "stop"
    },
    {
      "index": 1,
      "message": {"role": "assistant", "content": "单元测试是用一组输入和预期结果来检查函数或模块行为的测试。"},
      "finish_reason": "stop"
    }
  ]
}
```

`index` 只是候选编号。两条回答可以相同，接口也没有质量排名的约定。第一版 Agent 只需要一条候选，省略 `n` 即可。如果业务确实需要对比多个候选，就由上层自己设定规则，例如让两份代码分别跑同一组测试。  
[vLLM · 并行采样实现](https://docs.vllm.ai/en/latest/api/vllm/v1/engine/parallel_sampling/) · [OpenAI · Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

`n` 要看端点和模型是否支持。OpenAI 的部分较新模型会拒绝显式传入 `n`，Responses API 也没有这个参数，需要多条候选时可以分开请求。Responses 的 `output` 数组表示一次响应中的消息、函数调用等不同项目。  
[OpenAI · Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) · [OpenAI · 迁移到 Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)

## tool_choice 又是什么？

这是另一个容易混淆的名字。以 Chat Completions 为例，`tool_choice: "auto"` 允许模型根据上下文直接回答或请求工具，`"none"` 禁止调用工具，`"required"` 要求调用至少一个工具，接口也可以指定工具名。

拿天气问题来说，请求附带 `get_weather` 的定义，模型可以生成符合相应格式的工具请求。某些 vLLM 配置会从模型生成的内容里解析出工具名和参数，再放进 `choices[0].message.tool_calls`。随后由我们的 Agent 校验参数、执行查询并回传结果。

写第一版 Agent 时，读取一条 `choice`，然后检查它有没有 `tool_calls`。有工具请求就进入执行循环，读到最终回答就展示给用户。  
[OpenAI · 函数调用](https://developers.openai.com/api/docs/guides/function-calling) · [vLLM · Tool Calling](https://docs.vllm.ai/en/latest/features/tool_calling/)
