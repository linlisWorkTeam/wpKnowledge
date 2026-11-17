# 02｜从零写 Agent（一）· 模型是怎么跑起来的？

[上一篇](./01-model-api-agent-harness.md)分清了模型、API 和 Agent。接下来我们从零搭一个最小的 Agent：先让程序向模型发一条消息，再给模型接一个工具，最后把工具结果交回模型，让它决定下一步。这一篇先做第一件事，看看一条消息是怎么变成回答的。

## 先把模型当成一个函数

如果你平时写业务代码，可以把文本生成想成一次函数调用：

```python
reply = generate("用一句话解释什么是单元测试。")
```

这是应用看到的样子。再往里一层，模型由**网络结构和训练得到的权重**组成。以常见的自回归语言模型为例，输入文字会先拆成 token 并转成数字 ID，模型根据已有 token 给出下一个 token 的概率分布，生成程序选出一个 token，再把它接到序列末尾继续生成，直到遇到结束条件。用训练好的模型处理输入并生成结果，这个过程叫**推理（inference）**。  
[Hugging Face · Generation with LLMs](https://huggingface.co/docs/transformers/v4.33.0/en/llm_tutorial)

## 谁负责把模型跑起来？

你拿到一份模型权重后，还需要代码来加载它、把输入转成模型能处理的格式，并安排硬件执行计算。**vLLM** 就是做这件事的推理引擎之一。vLLM 可以在 Python 进程里直接运行推理，也可以通过 `vllm serve` 启动一个 HTTP 服务，让别的程序发送请求。  
[vLLM · Quickstart](https://docs.vllm.ai/en/latest/getting_started/quickstart/)

| 遇到的东西 | 在这一层负责什么 |
| --- | --- |
| 模型权重与配置 | 决定用哪个训练好的模型做计算 |
| vLLM 推理引擎 | 加载模型并运行推理 |
| HTTP 服务 | 接收请求，组织输入，调用推理引擎并返回结果 |
| LLM API | 约定调用者该请求哪个地址、传什么字段、怎么读取响应 |

所以，「LLM API 是推理框架暴露出来的服务」可以说得更精确一点：**API 是推理服务对外提供的调用接口**。自建时可以直接使用 vLLM 自带的 HTTP 服务。用托管服务时，你只需要按照供应商的 API 文档发请求，服务内部用什么推理引擎由供应商决定。

## 动手试一下：发出第一条模型请求

如果你已经按官方文档安装好 vLLM，并有兼容的运行环境，可以在本机用一个小模型试一下。先在第一个终端启动服务，等待模型加载完成。  
[vLLM · 安装与快速入门](https://docs.vllm.ai/en/latest/getting_started/quickstart/)

```bash
vllm serve Qwen/Qwen2.5-1.5B-Instruct --host 127.0.0.1 --port 8000
```

在第二个终端发送一条请求：

```bash
curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-1.5B-Instruct",
    "messages": [
      {"role": "user", "content": "用一句话解释什么是单元测试。"}
    ],
    "max_tokens": 80
  }'
```

这里的 `model` 指定已加载的模型，`messages` 是这次发给模型的对话，`max_tokens` 限制生成长度。请求成功后，回答正文在响应 JSON 的 `choices[0].message.content`。它可能是「单元测试用于验证一个函数或模块在给定输入下是否按预期工作。」  
[vLLM · OpenAI 兼容 HTTP 服务](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)

这里的 **OpenAI 兼容**指请求和响应遵循相应的 API 格式。这个例子的请求地址是本机，实际计算用的是 vLLM 加载的 Qwen。手头没有合适的运行环境，也可以用现成的托管模型 API 完成这一步，按提供方文档替换地址、鉴权、模型名和请求格式。

接下来我们会把这次请求封装成一个 `chat(messages)` 函数，作为 Agent 调用模型的入口。有了它，就可以加第一个工具：当模型提出要查询某条信息时，让我们的程序实际去查，再把结果放进下一次请求。
