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

## TODO
- HTTP API
- 完善log组件