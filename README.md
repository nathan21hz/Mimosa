<p align="center">
  <img height="128" width="128" src="./img/logo.png" />
</p>
<h1 align="center">Mimosa</h1>
<p align="center">一体化 <i>爬虫/数据监控/推送</i> 工具</p>


## 功能特点
- 爬虫、数据解析、推送均为模块化设计
- 配置文件/功能模块支持热重载

## 命令
- stop: 结束
- reload: 重载功能模块和任务配置文件
- start \<任务名\>: 开始任务
- stop \<任务名\>: 结束任务
- clear [任务名]: 清除任务历史数据
- save: 保存任务历史数据 

## 配置文件
> JSON， 默认为 config.json
- LOG_LEVEL: 日志级别，默认`0`
- TASK_FILE: 任务文件名，默认`tasks.json`
- HTTP_API: 是否打开HTTP API，默认`false`
- API_PORT: HTTP API端口，默认`8080`
- API_ALLOW_WRITE: 是否允许API进行控制，默认`false`
- API_VERIFY_URL: 认证用URL，默认为空
  > 当 API_VERIFY_URL 非空时，每次请求API时会先对该地址进行一次POST请求，request body为：
  ```
    {
      "url":"http://xxx:8080/api/tasks?token=xxxx",  # 发起请求的url
      "service":"mimosa"
    }
  ```
  > 当且仅当收到的响应为`0`时，继续处理请求，否则返回状态401。

## 任务文件
> JSON （详见tasks_demo.json），除以下配置项外可视需求添加，支持动态加载
### 动态加载任务
- name: 任务名，会替换掉动态加载的任务名
- type: `dynamic`
- config_source: 任务源，格式同 source 数据源
- update_interval: 任务配置更新间隔(s)

> 动态加载的文件格式同静态任务的一个任务项

### 静态任务
- name: 任务名
- type: `static`
- interval: 数据更新间隔（秒）
- startup_data: 启动时数据（作为首次爬取时的上一次变量）

#### source 数据源
> 模块存放于source文件夹下
- type: 模块名，须于文件名相同
- url: 请求域名，str / dict，支持动态获取（见下）
    > 所有以 `url` 开头的字段均支持动态获取 

    ##### url 动态获取
    > 当url为dict时
    - base: url生成模板，按format函数格式
    - source: 与 数据源 source 格式相同
    - data: 与 数据解析 data 格式相同
    > 动态获取的字段会被保存至 `*+原字段名` 字段中，如 `url` -> `*url`。
    
    > 在source数据源模块中建议使用带*字段名访问所有动态获取字段。

#### data 数据解析 
> 列表，模块存放于data文件夹下
- type: 模块名，须于文件名相同
- postprocess: 后处理，与data段格式相同

#### condition 条件判断 
> 列表
- conn: 与上个条件的逻辑连接，[and, or]，首个需为and
- var: 判断符前变量
- op: 判断符，[==, !=, <, >, <=, >=, in(list)]
- target: 判断符后变量

    ##### 变量
    > 以字符串类型输入以下内容时将解析为变量，否则以原样判断
    - $n: 本次更新的第n个数据
    - #n: 上次更新的第n个数据
    - *timestamp: 当前时间戳

#### push 推送 
> 推送配置，模块存放于push文件夹下
- type: 模块名，须于文件名相同

## HTTP API
#### [GET] /api/tasks 任务列表
response:
```
{
  "status":"success",
  "msg":"成功",
  "data":[
    {
      "name":"xxx",
      "type":"static",
      "running":true,
      "last_updat":"1970-01-01 08:00:00",
      "data":["test", 0]
    },
    ...
  ]
}
```
#### [GET] /api/tesk/\<name\> 任务详情
response:
```
{
  "status":"success",
  "msg":"成功",
  "data":
    {
      "name":"xxx",
      "type":"static",
      "running":true,
      "last_updat":"1970-01-01 08:00:00",
      "data":["test", 0]
      "raw":"......."    # 任务的原始配置
    }
}
```
#### [POST] /api/tasks 新增在线任务
仅支持`static` 任务，请求格式同任务配置文件，对在线任务会在其任务名前添加`online_`前缀。

request body:
```
[
    {
        "name":"test",
        "type":"static",
        "interval":300,
        "startup_data":[ ... ],
        "source":{ ... },
        "data":[ ... ],
        "condition":[ ... ],
        "push": { ... }
    }
]
```
#### [DELETE] /api/task/<name> 删除在线任务
仅支持删除在线任务

#### [POST] /api/task/\<name\>/running 开始/暂停任务
request body:
```
{
  "running":true # 开始  /  false # 暂停
}
```
response:
```
{
  "status":"success",
  "msg":"任务已开始",
  "data":{}
}
```
#### [POST] /api/task/\<name\>/clear 清空历史数据
response:
```
{
  "status":"success",
  "msg":"清理历史数据成功",
  "data":{}
}
```
#### [POST] /api/reload 重载任务配置
重载后在线任务将被删除

response:
```
{
  "status":"success",
  "msg":"重载成功",
  "data":{}
}
```

## TODO
- HTTP API 认证
- 完善log组件