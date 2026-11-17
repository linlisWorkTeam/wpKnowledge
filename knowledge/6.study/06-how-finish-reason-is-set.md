# 06｜从零写 Agent · finish_reason 是怎么生成的？

[上一篇](./05-how-model-choices-are-generated.md)讲到，模型按 token 一步步生成回复。每生成一段内容，推理服务会检查这条候选是否已经触发结束条件。生成结束后，API 服务在对应的 `choices[i].finish_reason` 里填入原因。**模型输出 token，服务端根据发生的事件填写 `finish_reason`。**

## 什么时候会返回 stop？

在 Chat Completions 里，最常见的两种情况是模型自然结束，或者生成内容命中了请求指定的停止序列。

**自然结束。** 假设你问「用一句话解释什么是单元测试」。模型生成正文后，下一步可能选出结束标记，例如 EOS（End of Sequence，序列结束）或模型定义的对话轮次结束标记。推理引擎识别这个特殊 token，结束当前序列，服务返回 `finish_reason: "stop"`。你在正文里通常看不到这个特殊 token。句号本身也可以被生成在段落中间，服务靠结束标记判断何时结束。  
[Hugging Face · 自回归生成](https://huggingface.co/docs/transformers/v4.33.0/en/llm_tutorial) · [vLLM · 结束 token 与解码参数](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)

**命中停止序列。** 在支持该参数的端点上，可以在请求里传入：

```json
{"stop": ["[END]"]}
```

如果模型这轮生成了 `单元测试用于验证代码单元的行为。[END]`，服务识别到 `[END]` 后就可以结束生成，`finish_reason` 同样是 `"stop"`。按 OpenAI Chat Completions 的约定，返回正文会去掉命中的停止序列。把 `[END]` 写在提示词里，可以用来告诉模型何时输出它。真正触发这个规则的是模型在**输出里**生成了它。不同端点和模型的参数支持范围以各自文档为准。  
[OpenAI · Chat Completions 的 stop 参数](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) · [vLLM · 增量解码与停止字符串匹配](https://docs.vllm.ai/en/latest/api/vllm/v1/engine/detokenizer/)

## length 和 tool_calls 又是怎么来的？

| 这轮发生了什么 | Chat Completions 返回值 | Agent 怎么处理 |
| --- | --- | --- |
| 自然结束，或命中指定停止序列 | `stop` | 按任务验收输出。例如要求 JSON 时，仍要解析并校验 |
| 达到生成长度上限 | `length` | 把输出当成可能有截断的内容，尤其要防止拿半截参数去调用工具 |
| 这轮返回了自定义工具请求 | `tool_calls` | 读取 `message.tool_calls`，校验参数，执行后回传结果 |
| 服务过滤了部分输出 | `content_filter` | 按应用的错误或提示逻辑处理 |

可以把结束原因分两层来看。推理引擎知道序列是触发了结束条件，还是用完了生成预算。API 层会把这些结果组织成协议字段，也会根据消息内容处理工具调用。例如在 vLLM 的 Chat Completions 实现里，服务解析出工具调用后，可以把这一候选的结束原因标成 `tool_calls`。到这一步结束的是**本次模型生成**，查询天气、读取资料等操作仍由应用执行。  
[OpenAI · Chat Completions 响应字段](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) · [vLLM · Chat Completions 响应组装示例](https://docs.vllm.ai/en/v0.23.0/api/vllm/entrypoints/openai/chat_completion/serving/)

写流式客户端时，前面的增量片段可能暂时没有结束原因，或者值是 `null`。等到候选的结束片段，再判断它为什么结束。对我们的最小 Agent 来说，`stop` 只能说明生成按停止条件收尾。任务是否完成，还要看正文和应用自己的验收条件。  
[OpenAI · Chat Completions 流式事件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events)
