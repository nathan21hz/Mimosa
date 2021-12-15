# All in One Push Service
> 个人使用的爬虫/推送整合工具

## 功能特点
- 爬虫、数据解析、推送均为模块化设计
- 配置文件/功能模块支持热重载

## 命令
- stop: 结束
- reload: 重载功能模块和配置文件
- clear [任务名]: 清除任务历史数据
- save: 保存任务历史数据 

## 配置文件
> JSON （详见config_demo.json），以下配置项为必须
- name: 任务名
- interval: 更新间隔（秒）
- startup_data: 启动时数据（作为首次爬取时的上一次变量）

### 数据源 source
> 模块存放于source文件夹下
- type: 模块名，须于文件名相同

### 数据解析 data
> 列表，模块存放于data文件夹下
- type: 模块名，须于文件名相同

### 条件判断 condition
> 列表
- conn: 与上个条件的逻辑连接，[and, or]，首个需为and
- var: 判断符前变量
- op: 判断符，[==, !=, <, >, <=, >=, in(list)]
- target: 判断符后变量

#### 变量
> 以字符串类型输入以下内容时将解析为变量，否则以原样判断
- $n: 本次更新的第n个数据
- #n: 上次更新的第n个数据
- *timestamp: 当前时间戳

### 推送 push
> 推送配置，模块存放于data文件夹下
- type: 模块名，须于文件名相同