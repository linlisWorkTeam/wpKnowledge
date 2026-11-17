# 03｜从零写 Agent（二）· LLM API 入门

[上一篇](./02-how-llm-inference-and-api-work.md)用 vLLM 加载模型，再用 `curl` 问它「用一句话解释什么是单元测试」。这篇从同一个例子出发，看看请求怎么发、响应怎么读，以及 Agent 什么时候该回答用户，什么时候还要执行工具。

## 同一句话怎么发给三种 API

下面省略了 HTTP 请求头，只对照 JSON 请求体。`YOUR_MODEL_ID` 要换成所用服务支持的模型 ID。三个例子都问同一个问题。

**OpenAI Chat Completions API · `POST /v1/chat/completions`**

```json
{
  "model": "YOUR_MODEL_ID",
  "messages": [{"role": "user", "content": "用一句话解释什么是单元测试。"}]
}
```

上一篇的 vLLM 示例用的就是这种请求格式。
[OpenAI · Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

**OpenAI Responses API · `POST /v1/responses`**

```json
{
  "model": "YOUR_MODEL_ID",
  "input": "用一句话解释什么是单元测试。"
}
```

简单提问可以用字符串作为 `input`，多轮或工具场景也可以传结构化的输入项。
[OpenAI · 从 Chat Completions 迁移到 Responses](https://developers.openai.com/api/docs/guides/migrate-to-responses)

**Anthropic Messages API · `POST /v1/messages`**

```json
{
  "model": "YOUR_MODEL_ID",
  "max_tokens": 128,
  "messages": [{"role": "user", "content": "用一句话解释什么是单元测试。"}]
}
```

这里同样有 `messages`，还要提供 `max_tokens`。响应的 `content` 是一个内容块数组，普通文本在 `type` 为 `text` 的块里。直接调用 Anthropic 的 API 时，请求还需要带相应的鉴权和 `anthropic-version` 请求头。
[Anthropic · Messages API](https://platform.claude.com/docs/en/api/messages/create)

各家服务最初按自己的产品需求设计接口。随着模型接入变多，大家逐渐形成了一些共同约定，例如用 `model` 字段选模型、用角色区分用户和助手的消息，以及用结构化数据表达工具调用。服务端也可以主动兼容已有格式，让客户端复用同一套代码。比如上一篇的 vLLM 用 OpenAI 兼容的端点提供 Qwen 推理，vLLM 也提供 Anthropic Messages 兼容端点。  
[vLLM · 兼容端点与支持范围](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)

所以，看到「OpenAI 兼容」，先问它**兼容的是哪个端点、支持哪些功能**。同样叫 OpenAI API，Chat Completions 和 Responses 的输入、输出结构也有差异。两家服务用同样的 JSON 接收普通文本，也可能在流式输出、工具调用或多轮状态处理上有不同的支持范围。

## 响应里有什么

沿用前面的 Chat Completions 请求，问「用一句话解释什么是单元测试」。下面是一份非流式响应的示意，省略了和本节无关的字段。Token 数字仅用于展示格式。

```json
{
  "id": "chatcmpl_example_1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "单元测试用来验证一个小的代码单元在给定输入下是否按预期工作。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 24,
    "completion_tokens": 19,
    "total_tokens": 43
  }
}
```

- **`choices[0].message.content`** 是可以展示给用户的正文。`choices` 是候选结果数组，示例里只有一个候选。
- **`finish_reason`** 说明这次生成为什么停止。后面会展开它是怎么生成的。
- **`usage`** 记录 token 用量。应用可以把它用在用量统计或成本估算里。
- **`id`** 标识这次响应，记录日志时可以用它关联请求和响应。

[OpenAI · Chat Completions 响应结构](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

### 三种 API 的响应字段

| 你想读什么 | Chat Completions | OpenAI Responses | Anthropic Messages |
| --- | --- | --- | --- |
| 用户能看到的文本 | `choices[].message.content` | 在 `output` 的消息项中找 `output_text` 内容块 | 在 `content` 中找 `text` 内容块 |
| 自定义工具请求 | `choices[].message.tool_calls`，用 `id` 关联结果 | `output` 中的 `function_call` 项，用 `call_id` 关联结果 | `content` 中的 `tool_use` 块，回传时用 `tool_use_id` 对应它的 `id` |
| 这一轮是否完成或截断 | `choices[].finish_reason`，如 `stop`、`length` | 看顶层 `status`，若为 `incomplete` 再看 `incomplete_details` | `stop_reason`，如 `end_turn`、`max_tokens` |
| Token 用量 | `usage.prompt_tokens`、`usage.completion_tokens` | `usage.input_tokens`、`usage.output_tokens` | `usage.input_tokens`、`usage.output_tokens` |

OpenAI SDK 的 `response.output_text` 可以汇总 Responses 的正文。Responses 的 `status: "completed"` 表示这次响应生成完成。程序还要检查 `output`，确认里面是否有等待应用执行的 `function_call`。  
[OpenAI · Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create) · [Anthropic · Messages API](https://platform.claude.com/docs/en/api/messages/create) · [Anthropic · 停止原因](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)

## choices 怎么生成

以常见的自回归语言模型为例。输入被转成 token 之后，模型为下一个位置上的候选 token 打分。推理引擎按解码策略选出一个，把它接到已有序列，再继续下一步。

比如给模型一个句子开头「单元测试主要用来」，下一步可能往「验证」这个方向接，也可能往「检查」这个方向接。下面用词来示意，实际计算按 token 进行。

- **贪心解码（greedy decoding）**每一步取当前得分最高的 token。
- **采样（sampling）**按调整后的概率抽取 token。`temperature` 可以改变概率分布的集中程度，`top_p` 可以限制采样范围。

一旦某一步选出的 token 不同，后面的输入序列也就不同了。这个差异可以让同一个问题得到两种措辞，甚至走向两种解法。  
[Hugging Face · Generation with LLMs](https://huggingface.co/docs/transformers/v4.33.0/en/llm_tutorial) · [vLLM · SamplingParams](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)

### n=2 时怎么返回两条回答？

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

## 有工具时要读什么

把问题换成「北京现在天气怎么样？」。假设你的程序在请求中声明了一个自定义工具 `get_weather`，请求参数 `tool_choice` 可以控制这一轮是否允许调用工具。`auto` 允许模型直接回答或请求工具，`none` 禁止调用，`required` 则要求调用至少一个工具，也可以指定工具名。下面是 Chat Completions 的示意响应。

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_weather_1",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\":\"北京\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

这份响应里已经有了三样东西：**工具名** `get_weather`、**参数** `{"city":"北京"}`、**调用 ID** `call_weather_1`。在 Chat Completions 里，`arguments` 是一段 JSON 字符串，应用要先解析并校验它，再调用已经登记的工具。查询结果用 `tool_call_id` 对应原来的 `call_weather_1`，再回传给模型，模型再根据结果组织回答。

这里的 `content` 是 `null`，因为这次回复只包含工具调用。有些回复也会同时带一段正文和工具请求，例如先说「我查一下」。**即使返回了文本，也要检查工具调用字段。** 一次 HTTP 请求成功，表示服务返回了这轮结果，用户的任务可能还要再走一轮。  
[OpenAI · 函数调用与工具结果回传](https://developers.openai.com/api/docs/guides/function-calling)

## finish_reason 什么时候是 stop

推理服务会检查生成是否触发了结束条件，API 层把原因写进 `choices[i].finish_reason`。在 Chat Completions 里，返回 `stop` 最常见的两种情况是模型自然结束，或生成内容命中了请求指定的停止序列。

**自然结束。** 假设你问「用一句话解释什么是单元测试」。模型生成正文后，下一步可能选出结束标记，例如 EOS（End of Sequence，序列结束）或模型定义的对话轮次结束标记。推理引擎识别这个特殊 token，结束当前序列，服务返回 `finish_reason: "stop"`。你在正文里通常看不到这个特殊 token。句号本身也可以被生成在段落中间，服务靠结束标记判断何时结束。  
[Hugging Face · 自回归生成](https://huggingface.co/docs/transformers/v4.33.0/en/llm_tutorial) · [vLLM · 结束 token 与解码参数](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)

**命中停止序列。** 在支持该参数的端点上，可以在请求里传入：

```json
{"stop": ["[END]"]}
```

如果模型这轮生成了 `单元测试用于验证代码单元的行为。[END]`，服务识别到 `[END]` 后就可以结束生成，`finish_reason` 同样是 `"stop"`。按 OpenAI Chat Completions 的约定，返回正文会去掉命中的停止序列。把 `[END]` 写在提示词里，可以用来告诉模型何时输出它。真正触发这个规则的是模型在**输出里**生成了它。不同端点和模型的参数支持范围以各自文档为准。  
[OpenAI · Chat Completions 的 stop 参数](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) · [vLLM · 增量解码与停止字符串匹配](https://docs.vllm.ai/en/latest/api/vllm/v1/engine/detokenizer/)

### 常见的结束原因

| 这轮发生了什么 | Chat Completions 返回值 | Agent 怎么处理 |
| --- | --- | --- |
| 自然结束，或命中指定停止序列 | `stop` | 按任务验收输出。例如要求 JSON 时，仍要解析并校验 |
| 达到生成长度上限 | `length` | 把输出当成可能有截断的内容，尤其要防止拿半截参数去调用工具 |
| 这轮返回了自定义工具请求 | `tool_calls` | 读取 `message.tool_calls`，校验参数，执行后回传结果 |
| 服务过滤了部分输出 | `content_filter` | 按应用的错误或提示逻辑处理 |

可以把结束原因分两层来看。推理引擎知道序列是触发了结束条件，还是用完了生成预算。API 层会把这些结果组织成协议字段，也会根据消息内容处理工具调用。例如在 vLLM 的 Chat Completions 实现里，服务解析出工具调用后，可以把这一候选的结束原因标成 `tool_calls`。到这一步结束的是**本次模型生成**，查询天气、读取资料等操作仍由应用执行。  
[OpenAI · Chat Completions 响应字段](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) · [vLLM · Chat Completions 响应组装示例](https://docs.vllm.ai/en/v0.23.0/api/vllm/entrypoints/openai/chat_completion/serving/)

## 流式响应怎么读

前面的例子一次收到完整 JSON。开启 `stream` 后，服务会陆续返回事件或片段，界面可以收到一点文本就显示一点。Chat Completions 的文本通常在 `choices[].delta.content`，Responses 有 `response.output_text.delta` 事件，Anthropic Messages 有包含 `text_delta` 的 `content_block_delta` 事件。工具参数也可能分成几段传过来，需要等对应调用收齐，再解析和执行。Chat Completions 的前几个片段里，`finish_reason` 可能是 `null`，要等候选结束时再判断。  
[OpenAI · Chat Completions 流式事件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) · [OpenAI · Responses 流式输出](https://developers.openai.com/api/docs/guides/streaming-responses) · [Anthropic · Messages 流式输出](https://platform.claude.com/docs/en/build-with-claude/streaming)

第一版 Agent 可以先用非流式的 Chat Completions，把 HTTP 请求和响应解析放在 `chat(messages)` 里。上层拿到正文、工具请求和结束状态，再决定要执行工具并回传，还是按任务要求交付结果。
