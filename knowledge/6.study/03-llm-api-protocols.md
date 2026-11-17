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

沿用前面的 Chat Completions 请求，问「用一句话解释什么是单元测试」。下面是一份非流式响应示意，时间戳和 token 数都只是示例。

```json
{
  "id": "chatcmpl_example_1",
  "object": "chat.completion",
  "created": 1780000000,
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "单元测试用来验证一个小的代码单元在给定输入下是否按预期工作。"
      },
      "logprobs": null,
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

### 响应对象和候选消息

| 字段 | 类型 | 怎么理解 |
| --- | --- | --- |
| `id` | 字符串 | 这份生成响应的标识。可以记入日志，便于定位某次生成。一份响应可能包含多个候选和工具调用，它们各有自己的编号或 ID。 |
| `object` | 字符串 | 响应对象的类型。`chat.completion` 是完整响应，流式增量通常是 `chat.completion.chunk`。 |
| `created` | 整数 | 响应的创建时间，Unix 时间戳，单位是秒。 |
| `model` | 字符串 | 服务端报告的模型标识。接入层做日志或统计时，可以和请求里填的模型名一起记录。 |
| `choices` | 数组 | 这次生成的候选回复。普通问答通常只有一项，支持多候选的端点可以返回多项。 |
| `choices[].index` | 整数 | 从 0 开始的候选编号。流式时可以用它把属于同一候选的片段拼起来。 |
| `choices[].message` | 对象 | 一条完整的助手消息，可能有正文、工具请求，或同时包含两者。 |
| `message.role` | 字符串 | 消息的角色。这里是 `assistant`，表示这是助手生成的消息。多轮调用时可以把这条消息放回对话记录。 |
| `message.content` | 字符串或 `null` | 助手的正文。只有工具请求时可能为 `null`，此时去读同一条消息的 `tool_calls`。 |
| `message.refusal` | 可选字符串或 `null` | 模型返回的拒绝说明。程序可以单独展示或记录这段说明。 |
| `choices[].finish_reason` | 字符串 | 此候选为什么结束。常见值有 `stop`、`length`、`tool_calls` 和 `content_filter`，后面有逐项说明。 |
| `choices[].logprobs` | 对象或 `null` | 支持的模型在开启 `logprobs` 后，可以返回输出 token 的对数概率。里面的 `token` 是该位置生成的 token，`logprob` 是它的对数概率，`top_logprobs` 列出同一位置的备选 token 及其概率信息，`bytes` 可用于按原始 UTF-8 字节还原文本。这些分数描述单个 token 的生成概率，答案是否正确仍要单独判断。 |

部分服务还会返回 `service_tier`，表示处理这次请求使用的服务档位。旧响应里也可能看到已弃用的 `system_fingerprint`，用于标识后端配置。兼容端点实际返回的可选字段以它自己的文档为准。  
[OpenAI · Chat Completions 响应结构](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

### usage 里的 token 怎么数

| 字段 | 怎么理解 |
| --- | --- |
| `usage` | 这次请求的用量统计。它属于整个响应，和单个候选的 `finish_reason` 在不同层。 |
| `usage.prompt_tokens` | 这轮输入使用的 token。输入可能包括用户消息、系统指令、对话历史和工具定义，所以通常比只数用户这一句得到的数字大。 |
| `usage.completion_tokens` | 这轮生成使用的 token。文本、生成的工具参数以及模型内部推理都可能计入，具体以模型和接口的统计规则为准。 |
| `usage.total_tokens` | 输入和输出 token 的合计。示例里是 `24 + 19 = 43`。 |
| `usage.prompt_tokens_details.cached_tokens` | 输入中命中缓存的 token 数，是 `prompt_tokens` 的一部分。 |
| `usage.completion_tokens_details.reasoning_tokens` | 输出中用于内部推理的 token 数，是 `completion_tokens` 的一部分。 |

做用量统计时用总数，做成本估算时按供应商的输入、缓存命中和输出价格分别计算。缓存和推理明细属于已有的总数，计算 token 总量时无需再加一次。  
[OpenAI · Chat Completions 用量字段](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

### 换成 Responses 或 Messages 去哪里读

| 要读取的信息 | Chat Completions | OpenAI Responses | Anthropic Messages |
| --- | --- | --- | --- |
| 正文 | `choices[].message.content` | `output[].content[]` 中 `type: "output_text"` 的块，正文在 `text` | `content[]` 中 `type: "text"` 的块，正文在 `text` |
| 工具请求 | `message.tool_calls[]` | `output[]` 中 `type: "function_call"` 的项 | `content[]` 中 `type: "tool_use"` 的块 |
| 关联工具结果 | 请求里的 `tool_call_id` 对应调用的 `id` | 结果项 `function_call_output` 的 `call_id` 对应调用的 `call_id` | 结果块 `tool_result` 的 `tool_use_id` 对应调用的 `id` |
| 生成状态 | 各候选的 `finish_reason` | 顶层 `status`，必要时读 `incomplete_details` 或 `error` | 顶层 `stop_reason`，自定义停止序列看 `stop_sequence` |
| Token 用量 | `prompt_tokens`、`completion_tokens`、`total_tokens` | `input_tokens`、`output_tokens`、`total_tokens` | `input_tokens`、`output_tokens`，缓存输入单独列出 |

**Responses 的 `output` 按项目类型解析。** 遍历 `output`，找到 `type: "message"` 的项，再到它的 `content` 数组里取 `output_text` 块。数组里还可能有 `reasoning` 项或 `function_call` 项，所以第一项的位置不能固定用来取正文。OpenAI SDK 的 `response.output_text` 会汇总正文，工具调用仍要从 `output` 读。函数调用项里的 `name` 是工具名，`arguments` 是 JSON 字符串，`call_id` 是回传结果用的关联键。

Responses 的 `status: "completed"` 表示这次响应生成完成，应用可能还要执行工具。`incomplete` 表示响应未生成完整，可以看 `incomplete_details.reason` 了解原因，例如 `max_output_tokens`。`failed` 时查看 `error`。用量里的 `input_tokens_details.cached_tokens` 和 `output_tokens_details.reasoning_tokens` 分别是输入与输出的子项。  
[OpenAI · Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create) · [OpenAI · 迁移到 Responses](https://developers.openai.com/api/docs/guides/migrate-to-responses)

**Messages 的 `content` 按内容块类型解析。** 顶层 `id` 标识助手消息，`role` 是 `assistant`，`model` 是模型标识。`text` 块里读 `text`，`tool_use` 块里读 `id`、`name` 和 `input`。这里的 `input` 已经是 JSON 对象，可以直接做参数校验。常见的 `stop_reason` 有 `end_turn`（自然结束）、`max_tokens`（到达生成上限）和 `tool_use`（提出了工具请求）。如果是 `stop_sequence`，同名字段 `stop_sequence` 会告诉你命中了哪段字符串。

Anthropic 官方的缓存统计采用另一套口径。用量里的 `input_tokens` 是未计入缓存读写的输入部分，`cache_read_input_tokens` 是读缓存的 token，`cache_creation_input_tokens` 是写缓存的 token。启用缓存时，三项相加才是完整输入量。  
[Anthropic · Messages API](https://platform.claude.com/docs/en/api/messages/create) · [Anthropic · 停止原因](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons) · [Anthropic · 缓存用量](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

## 一次天气查询怎么跑完

用户只问了一句「上海今天的天气怎么样？」。Agent 先把问题和工具定义发给模型，收到工具调用后执行查询，再发第二次模型请求。下面沿用 Qwen2.5 + vLLM 的 Chat Completions 接口。天气结果为模拟数据，响应省略了无关字段。

### 1. Agent 发请求并声明工具

向 `POST /v1/chat/completions` 发送请求。工具定义里的 `name` 供程序查找已注册的函数，`description` 帮模型判断什么时候该用它，`tools[].function.parameters` 用 JSON Schema 描述函数接受什么参数。这里要求传入字符串类型的 `city`。`tool_choice: "auto"` 允许模型根据问题直接回答或提出工具调用。Chat Completions 也支持通过 `none`、`required` 或指定工具来进一步控制是否调用。

```json
{
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "messages": [
    {
      "role": "user",
      "content": "上海今天的天气怎么样？"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "查询指定城市今天的天气",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "城市名，例如上海"
            }
          },
          "required": [
            "city"
          ],
          "additionalProperties": false
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

在 vLLM 中复现这个自动工具调用示例时，Qwen2.5 的 Hermes 风格模板可配合 `--enable-auto-tool-choice --tool-call-parser hermes` 使用。模板会把消息角色、工具描述和参数 schema 按模型熟悉的格式组织进输入。  
[vLLM · 工具调用和 Qwen2.5 配置](https://docs.vllm.ai/en/stable/features/tool_calling/) · [OpenAI · 函数调用](https://developers.openai.com/api/docs/guides/function-calling)

### choices 怎么生成

模型为下一个位置的候选 token 打分。推理引擎可以选得分最高的 token（贪心解码），也可以按概率采样。`temperature` 可以调整概率分布的集中程度，`top_p` 可以限制采样范围。选中的 token 接回已有序列，参与下一步生成；生成的 token ID 再由解码器还原成文本或标记。

每个 `choice` 对应一整条候选回复，`index` 是它在候选列表里的序号。API 服务把生成与解析结果填进 `choices[i].message`。我们先看一条候选里出现工具调用是什么样。

### 有工具时要读什么

Qwen2.5 可以生成下面这样的中间文本。这里把模型模板使用的回合结束标记也一并展示。

```text
<tool_call>
{"name":"get_weather","arguments":{"city":"上海"}}
</tool_call><|im_end|>
```

vLLM 的解析器识别 `<tool_call>`，提取函数名和参数，由 API 层放进 `message.tool_calls`。客户端收到的是下面这份 Chat Completions JSON。

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
              "arguments": "{\"city\":\"上海\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

| 字段 | 怎么理解 |
| --- | --- |
| `message.tool_calls` | 助手提出的工具请求列表。每个元素表示一次调用。 |
| `tool_calls[].id` | API 响应中单次调用的标识。同名工具可以调用多次，回传结果时用 `tool_call_id` 匹配对应的 `id`。 |
| `tool_calls[].type` | 示例值为 `function`，详细数据放在 `function` 对象里。 |
| `function.name` | 注册的函数名，这里是 `get_weather`。 |
| `function.arguments` | 解码外层响应 JSON 后，这个值仍是一段字符串。再解析一次会得到 `{"city":"上海"}`，执行前还要校验字段和值。 |

此处 `content` 为 `null`。同一条消息也可能先说「我查一下」，再附带工具请求。程序应检查 `tool_calls`，并保留完整助手消息供下一轮使用。  
[Qwen2.5 · Tokenizer 与聊天模板](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/main/tokenizer_config.json) · [OpenAI · Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

### finish_reason 什么时候是 stop

推理引擎检查停止条件，API 层结合生成状态和解析结果填写 `finish_reason`。模型用哪个 token 来结束一轮，取决于模型和聊天模板。例如 Llama 3.1 的 `<|eot_id|>` 是轮次结束标记，Qwen2.5 的模板用 `<|im_end|>` 结束一条消息。这些标记属于模型自己的格式，客户端一般在响应字段里读取结束原因。

| Chat Completions 值 | 什么时候会出现 |
| --- | --- |
| `stop` | 模型自然结束，例如生成 EOS 或轮次结束标记，也可以是命中了请求指定的停止序列。支持 `stop` 参数的端点可以接收 `{"stop":["[END]"]}`，输出命中该字符串时停止，按 OpenAI 的约定返回正文会去掉该字符串。 |
| `length` | 达到生成长度上限，正文或工具参数可能被截断。 |
| `tool_calls` | 这一轮的响应交回了工具调用请求。上例虽出现了 Qwen 的结束标记，API 仍可根据解析出的调用填 `tool_calls`。 |
| `content_filter` | 服务因内容过滤省略了输出。 |
| `function_call` | 旧的函数调用结束原因，已弃用。新接入通常读取 `tool_calls`。 |
| `null` | 流式中间片段暂时没有结束原因，等对应候选的结束片段再判断。 |

[Meta · Llama 3.1 消息格式](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/prompt_format.md) · [OpenAI · Chat Completions 流式事件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) · [vLLM · 响应组装示例](https://docs.vllm.ai/en/v0.23.0/api/vllm/entrypoints/openai/chat_completion/serving/)

### 2. Agent 执行工具并把结果交回模型

Agent 解析 `arguments`，检查工具是否已注册、参数是否符合 schema、城市是否与用户请求一致，再执行 `get_weather(city="上海")`。假设工具返回上海多云，最高 24℃、最低 18℃。Agent 用同一个模型发第二次请求，`model`、`tools` 和 `tool_choice` 沿用首轮。第二次请求的 `messages` 如下：

```json
[
  {
    "role": "user",
    "content": "上海今天的天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_weather_1",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\":\"上海\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_weather_1",
    "content": "{\"city\":\"上海\",\"condition\":\"多云\",\"high_c\":24,\"low_c\":18}"
  }
]
```

最后一条的 `role: "tool"` 表明内容来自工具，`tool_call_id` 把结果关联到上一条助手消息的调用，`content` 是应用序列化后的工具结果。模型读到结果后，可以生成下面的最终回答：

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "上海今天多云，最高 24℃，最低 18℃。"
      },
      "finish_reason": "stop"
    }
  ]
}
```

第一轮的 `tool_calls` 让 Agent 继续执行。第二轮的 `stop` 表示这次生成已结束，Agent 可以在检查输出后把正文交给用户。  
[OpenAI · Chat Completions 工具结果回传](https://developers.openai.com/api/docs/guides/function-calling)

### Schema、训练和约束解码分别做什么

| 层次 | 在天气例子里负责什么 |
| --- | --- |
| 请求与模板 | `tools[].function.parameters` 描述 `get_weather` 的参数。Chat Completions 的 `response_format` 可约束助手回答的结构，例如要求天气总结按给定 JSON Schema 输出。调用参数和最终回答可以各有一份 schema。 |
| 模型训练 | 工具调用相关训练让模型更容易从工具描述和上下文判断要不要查天气、选哪个工具、从问题里取得城市。 |
| 推理引擎 | 在已启用且服务支持的严格模式下，约束解码根据已生成的前缀和 schema，在每步采样前屏蔽会让输出无法继续满足约束的候选 token。 |
| Agent | 校验解析后的参数、核对城市、执行工具，处理截断、拒绝或工具错误。 |

以本例的 schema 为例，`{"city":"北京"}` 有必填字段，值也是字符串，结构校验能够通过。但用户问的是上海，Agent 仍要检查参数的业务含义。严格结构化输出需要端点、模型和 schema 同时受支持，并且要等输出正常完成。普通 JSON 模式和严格 schema 约束的支持范围也各有不同。  
[OpenAI · Structured Outputs 原理](https://openai.com/index/introducing-structured-outputs-in-the-api/) · [OpenAI · Structured Outputs 用法](https://developers.openai.com/api/docs/guides/structured-outputs) · [vLLM · 工具调用约束](https://docs.vllm.ai/en/stable/features/tool_calling/)

### 同一模型怎么适配不同 API

服务端可以理解不同 API 的请求，再用聊天模板把消息、工具定义和工具结果转换成模型能读的输入。生成后，服务端可以把解析出的同一次天气调用封装成 Chat Completions 的 `message.tool_calls`、Responses 的 `function_call`，或 Anthropic Messages 的 `tool_use`。工具结果回传时也要转换对应的关联 ID。

字段能够转换，功能还要看整条链路。模型要能产出工具调用，模板要能表示工具定义和历史，解析器要能识别模型使用的标记，服务端要实现对应的流式事件和严格 schema 约束。接入时按目标端点实际支持的能力来判断。  
[vLLM · 兼容端点](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/) · [OpenAI · Responses 迁移指南](https://developers.openai.com/api/docs/guides/migrate-to-responses) · [Anthropic · Messages API](https://platform.claude.com/docs/en/api/messages/create)

### 流式响应怎么读

前面的例子一次收到完整 JSON。开启 `stream` 后，服务会陆续返回事件或片段，界面可以收到一点文本就显示一点。Chat Completions 的文本通常在 `choices[].delta.content`，Responses 有 `response.output_text.delta` 事件，Anthropic Messages 有包含 `text_delta` 的 `content_block_delta` 事件。工具参数也可能分成几段传过来，需要等对应调用收齐，再解析和执行。Chat Completions 的前几个片段里，`finish_reason` 可能是 `null`，要等候选结束时再判断。  
[OpenAI · Chat Completions 流式事件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) · [OpenAI · Responses 流式输出](https://developers.openai.com/api/docs/guides/streaming-responses) · [Anthropic · Messages 流式输出](https://platform.claude.com/docs/en/build-with-claude/streaming)

#### n=2 时怎么返回两条回答？

回到前面的单元测试示例，在 vLLM 兼容端点上，可以在请求里加上 `n: 2`，要求服务基于同一个输入生成两个候选。下面是发给 `POST /v1/chat/completions` 的示例请求体：

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

第一版 Agent 可以先用非流式 Chat Completions，把请求和响应解析放进 `chat(messages)`，再用上面的工具执行和结果回传跑完一次交互。
