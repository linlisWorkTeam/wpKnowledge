# 04｜从零写 Agent（三）· 模型 API 会返回什么？

[上一篇](./03-llm-api-protocols.md)把同一句话发给了三种 API。我们现在站在调用方这边看：收到响应后，程序应该把什么展示给用户，又该在什么时候继续执行？

## 普通问答返回一条助手消息

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
- **`finish_reason`** 说明这次生成为什么停止。这里的 `stop` 表示模型到达正常停止点，或命中了设定的停止序列。如果是 `length`，说明生成达到了长度限制，正文可能被截断。
- **`usage`** 记录 token 用量。应用可以把它用在用量统计或成本估算里。
- **`id`** 标识这次响应，记录日志时可以用它关联请求和响应。

所以最简单的聊天程序，拿到这条响应就可以显示 `content`。写 Agent 时，还需要看这次响应里面有没有让程序继续做的事。  
[OpenAI · Chat Completions 响应结构](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

## 有工具时，模型可能先返回一份调用请求

把问题换成「北京现在天气怎么样？」。假设你的程序在请求中声明了一个自定义工具 `get_weather`，模型就可能返回下面这样的消息：

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

这份响应里已经有了三样东西：**工具名** `get_weather`、**参数** `{"city":"北京"}`、**调用 ID** `call_weather_1`。在 Chat Completions 里，`arguments` 是一段 JSON 字符串，应用要先解析并校验它，再调用已经登记的工具。查询结果通过同一个调用 ID 回传给模型，模型再根据结果组织回答。

这里的 `content` 是 `null`，因为这次回复只包含工具调用。有些回复也会同时带一段正文和工具请求，例如先说「我查一下」。**即使返回了文本，也要检查工具调用字段。** 一次 HTTP 请求成功，表示服务返回了这轮结果，用户的任务可能还要再走一轮。  
[OpenAI · 函数调用与工具结果回传](https://developers.openai.com/api/docs/guides/function-calling)

## 换 API 时，去哪里读这些字段？

| 你想读什么 | Chat Completions | OpenAI Responses | Anthropic Messages |
| --- | --- | --- | --- |
| 用户能看到的文本 | `choices[].message.content` | 在 `output` 的消息项中找 `output_text` 内容块 | 在 `content` 中找 `text` 内容块 |
| 自定义工具请求 | `choices[].message.tool_calls`，用 `id` 关联结果 | `output` 中的 `function_call` 项，用 `call_id` 关联结果 | `content` 中的 `tool_use` 块，回传时用 `tool_use_id` 对应它的 `id` |
| 这一轮是否完成或截断 | `choices[].finish_reason`，如 `stop`、`length` | 看顶层 `status`，若为 `incomplete` 再看 `incomplete_details` | `stop_reason`，如 `end_turn`、`max_tokens` |
| Token 用量 | `usage.prompt_tokens`、`usage.completion_tokens` | `usage.input_tokens`、`usage.output_tokens` | `usage.input_tokens`、`usage.output_tokens` |

Responses 的 `status: "completed"` 表示这次响应生成完成。程序还要检查 `output`，确认里面是否有等待应用执行的 `function_call`。  
[OpenAI · Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create) · [Anthropic · Messages API](https://platform.claude.com/docs/en/api/messages/create) · [Anthropic · 停止原因](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)

## 流式输出是同一轮响应分批到达

前面的例子一次收到完整 JSON。开启 `stream` 后，服务会陆续返回事件或片段，界面可以收到一点文本就显示一点。Chat Completions 的文本通常在 `choices[].delta.content`，Responses 有 `response.output_text.delta` 事件，Anthropic Messages 有包含 `text_delta` 的 `content_block_delta` 事件。工具参数也可能分成几段传过来，需要等对应调用收齐，再解析和执行。  
[OpenAI · Chat Completions 流式事件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) · [OpenAI · Responses 流式输出](https://developers.openai.com/api/docs/guides/streaming-responses) · [Anthropic · Messages 流式输出](https://platform.claude.com/docs/en/build-with-claude/streaming)

我们先用非流式响应写第一版 `chat(messages)`。它把**正文、工具请求、结束原因和用量**交给上层。接下来的 Agent 循环就可以根据结果决定：把正文交给用户，还是执行工具并带着结果再请求一轮。
