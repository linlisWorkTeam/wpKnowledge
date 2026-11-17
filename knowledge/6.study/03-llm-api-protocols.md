# 03｜从零写 Agent（二）· LLM API 为什么有好几种？

[上一篇](./02-how-llm-inference-and-api-work.md)里，我们启动了 vLLM，然后用 `curl` 请求 `/v1/chat/completions`。如果把例子换成 OpenAI 或 Anthropic 的托管服务，你可能会看到另外两个名字：**Responses API** 和 **Messages API**。

这里的 Responses 和 Messages 是 API 的名字，Anthropic 是厂商。它们都能让程序发消息给模型、拿回回答。实际接入时，要看服务端规定的请求路径、字段和响应结构。

## 同一句话，三种请求怎么写？

下面省略了 HTTP 请求头，只对照 JSON 请求体。`YOUR_MODEL_ID` 要换成所用服务支持的模型 ID。三个例子都问同一个问题。

**OpenAI Chat Completions API · `POST /v1/chat/completions`**

```json
{
  "model": "YOUR_MODEL_ID",
  "messages": [{"role": "user", "content": "用一句话解释什么是单元测试。"}]
}
```

普通文本回答从 `choices[0].message.content` 读取。上一篇的 vLLM 示例用的就是这种请求格式。  
[OpenAI · Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

**OpenAI Responses API · `POST /v1/responses`**

```json
{
  "model": "YOUR_MODEL_ID",
  "input": "用一句话解释什么是单元测试。"
}
```

简单提问可以用字符串作为 `input`，多轮或工具场景也可以传结构化的输入项。原始 HTTP 响应在 `output` 数组里返回带类型的项目，例如消息、推理项和函数调用。读正文时，找消息项目中的 `output_text` 内容块。使用 OpenAI SDK 时，也可以用 `response.output_text` 直接取汇总后的文本。  
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

## 大家逐渐统一了什么？

各家服务最初按自己的产品需求设计接口。随着模型接入变多，大家逐渐形成了一些共同约定，例如用 `model` 字段选模型、用角色区分用户和助手的消息，以及用结构化数据表达工具调用。服务端也可以主动兼容已有格式，让客户端复用同一套代码。比如上一篇的 vLLM 用 OpenAI 兼容的端点提供 Qwen 推理，vLLM 也提供 Anthropic Messages 兼容端点。  
[vLLM · 兼容端点与支持范围](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)

所以，看到「OpenAI 兼容」，先问它**兼容的是哪个端点、支持哪些功能**。同样叫 OpenAI API，Chat Completions 和 Responses 的输入、输出结构也有差异。两家服务用同样的 JSON 接收普通文本，也可能在流式输出、工具调用或多轮状态处理上有不同的支持范围。

## 写 Agent 时，把这些差异放在哪里？

第一版 Agent 可以先接上一篇示例用的 Chat Completions 格式，把 HTTP 地址、鉴权、请求组装和响应解析放在一个 `chat(messages)` 函数里。上层传入消息，用返回值继续处理任务。以后换接口时，就知道该到哪里改。

等接入工具，这个函数还要把模型的工具请求交给上层。比如同样是请求调用 `get_weather`，Chat Completions 把它放在助手消息的 `tool_calls`，Responses 把它表示成 `function_call` 输出项，Anthropic Messages 用 `tool_use` 内容块。Agent 这一层关心的是同一件事：**模型想调哪个工具、参数是什么、结果该对应哪次调用。** 下一步就用一个工具把这个往返跑通。  
[OpenAI · 函数调用](https://developers.openai.com/api/docs/guides/function-calling) · [Anthropic · 工具调用](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
