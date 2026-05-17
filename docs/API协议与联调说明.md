# API 协议与联调说明

## 1. 文档目的

本文档说明四个系统之间如何联调：

- 学院 A 选课系统
- 学院 B 选课系统
- 学院 C 选课系统
- 数据集成服务器

目标是让四个系统可以完成以下业务：

- 查询共享课程
- 学生跨院选课
- 选课结果回写到原课程所在学院
- 学生退选课程
- 集成服务器统计三院数据

## 2. 联调原则

- 四个系统统一通过 HTTP 接口联调。
- 数据交换以 XML 为主，便于体现作业要求。
- 学院系统负责本院用户登录、课程展示、选课与退选操作。
- 集成服务器负责共享课程汇总、跨院选课协调、退选协调与统计汇总。
- 每个接口都应返回统一格式的结果，便于前端和其他系统处理。

## 3. 系统分工

### 3.1 学院 A/B/C 选课系统

每个学院系统都包含：

- 登录界面
- 本院课程管理
- 共享课程查看
- 选课与退课入口
- 接收集成服务器回写结果的接口

### 3.2 数据集成服务器

集成服务器包含：

- 共享课程汇总接口
- 跨院选课受理接口
- 退课协调接口
- 统计汇总接口
- 回写各学院结果的调用逻辑

## 4. 接口设计约定

### 4.1 通用约定

- 请求方式：`GET`、`POST`
- 请求格式：`application/xml`
- 响应格式：`application/xml`
- 所有时间字段统一使用 `yyyy-MM-dd HH:mm:ss`
- 所有返回值都包含 `code`、`message`、`data` 三部分
- `code=0` 表示成功，其它值表示失败

### 4.2 统一 XML Schema 约定

- 共享课程数据统一采用 `formatClass.xsd`，核心元素为 `classes/class/id/name/time/score/teacher/location`。
- 学生数据统一采用 `formatStudent.xsd`，核心元素为 `students/student/id/name/major`。
- 选课数据统一采用 `formatClassChoice.xsd`，核心元素为 `choices/choice/sid/cid/score`。
- 接口如需携带学院路由、请求时间、状态等业务信息，可放在外层请求封装中；核心业务数据仍按统一 Schema 传输。

### 4.3 幂等与错误处理约定

- 选课提交接口需要支持幂等处理：同一学生对同一课程的重复提交，不应生成重复选课记录。
- 退选接口同样需要支持幂等处理：同一条选课记录被重复退选时，应返回相同的最终结果，避免重复扣减或重复写回。
- 若课程已满、学院不可达或请求参数非法，接口应返回明确的错误码与错误信息。
- 若请求中的 `enrollmentId` 不存在，系统应返回“未找到”的错误响应。
- 对于跨院写回失败，集成服务器应保留原始请求状态，并允许后续重试。

### 4.4 常见错误码建议

| 场景                | 建议返回码 | 说明                                                   |
| ------------------- | ---------- | ------------------------------------------------------ |
| 重复选课            | `409`      | 当前学生已对该课程提交过选课请求，或已存在有效选课记录 |
| 课程已满            | `400`      | 课程剩余名额不足，无法继续选课                         |
| 学院不可达          | `503`      | 目标学院服务暂时不可用，建议稍后重试                   |
| 非法 `enrollmentId` | `404`      | 指定的选课记录不存在                                   |

#### 错误返回示例

```xml
<Response>
  <code>409</code>
  <message>duplicate enrollment</message>
  <data>
    <enrollmentId>E202605170001</enrollmentId>
    <status>EXISTS</status>
  </data>
</Response>
```

```xml
<Response>
  <code>400</code>
  <message>course is full</message>
  <data>
    <courseId>C001</courseId>
    <remain>0</remain>
  </data>
</Response>
```

```xml
<Response>
  <code>503</code>
  <message>college unavailable</message>
  <data>
    <collegeId>A</collegeId>
  </data>
</Response>
```

```xml
<Response>
  <code>404</code>
  <message>enrollment not found</message>
  <data>
    <enrollmentId>E999999999999</enrollmentId>
  </data>
</Response>
```

### 4.5 统一返回格式示例

```xml
<Response>
  <code>0</code>
  <message>success</message>
  <data>
    ...
  </data>
</Response>
```

## 5. 数据集成服务器接口

### 5.1 查询共享课程列表

用于学院系统从集成服务器获取可共享课程目录。

- URL：`/api/v1/shared-courses`
- 方法：`GET`
- 说明：按学院编码或课程关键词查询共享课程。

#### 请求示例

```http
GET /api/v1/shared-courses?collegeId=A HTTP/1.1
Host: integration-server.local
Accept: application/xml
```

#### 返回示例

```xml
<Response>
  <code>0</code>
  <message>success</message>
  <data>
    <meta>
      <collegeId>A</collegeId>
    </meta>
    <classes>
      <class>
        <id>C001</id>
        <name>数据库系统</name>
        <time>32</time>
        <score>3</score>
        <teacher>张老师</teacher>
        <location>1-301</location>
      </class>
      <class>
        <id>C018</id>
        <name>数据仓库基础</name>
        <time>24</time>
        <score>2</score>
        <teacher>李老师</teacher>
        <location>2-205</location>
      </class>
    </classes>
  </data>
</Response>
```

### 5.2 提交选课请求

学生在某学院系统中选择共享课程后，由学院系统调用集成服务器提交选课请求。

- URL：`/api/v1/enrollments`
- 方法：`POST`
- 说明：集成服务器接收后，决定写回到原课程所在学院。

#### 请求示例

```http
POST /api/v1/enrollments HTTP/1.1
Host: integration-server.local
Content-Type: application/xml
Accept: application/xml
```

```xml
<EnrollmentRequest>
  <meta>
    <homeCollegeId>C</homeCollegeId>
    <targetCollegeId>A</targetCollegeId>
    <requestTime>2026-05-17 10:30:00</requestTime>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>C001</cid>
      <score>0</score>
    </choice>
  </choices>
</EnrollmentRequest>
```

#### 返回示例

```xml
<Response>
  <code>0</code>
  <message>enrollment accepted</message>
  <data>
    <enrollmentId>E202605170001</enrollmentId>
    <status>PENDING_WRITEBACK</status>
    <targetCollegeId>A</targetCollegeId>
  </data>
</Response>
```

### 5.3 退选课程

学生退选课程时，由学院系统调用集成服务器统一处理。

- URL：`/api/v1/enrollments/{enrollmentId}/withdraw`
- 方法：`POST`
- 说明：集成服务器根据选课记录找到原课程所在学院并发起退选回写。

#### 请求示例

```http
POST /api/v1/enrollments/E202605170001/withdraw HTTP/1.1
Host: integration-server.local
Content-Type: application/xml
Accept: application/xml
```

```xml
<WithdrawRequest>
  <meta>
    <requestTime>2026-05-17 11:00:00</requestTime>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>C001</cid>
      <score>0</score>
    </choice>
  </choices>
</WithdrawRequest>
```

#### 返回示例

```xml
<Response>
  <code>0</code>
  <message>withdraw accepted</message>
  <data>
    <enrollmentId>E202605170001</enrollmentId>
    <status>WITHDRAW_PENDING</status>
  </data>
</Response>
```

### 5.4 统计汇总

用于查看三院学生、课程与选课的汇总数据。

- URL：`/api/v1/stats/summary`
- 方法：`GET`
- 说明：可用于管理端和报告展示。

#### 请求示例

```http
GET /api/v1/stats/summary HTTP/1.1
Host: integration-server.local
Accept: application/xml
```

#### 返回示例

```xml
<Response>
  <code>0</code>
  <message>success</message>
  <data>
    <Summary>
      <college>
        <collegeId>A</collegeId>
        <studentCount>50</studentCount>
        <courseCount>10</courseCount>
        <enrollmentCount>250</enrollmentCount>
      </college>
      <college>
        <collegeId>B</collegeId>
        <studentCount>50</studentCount>
        <courseCount>10</courseCount>
        <enrollmentCount>250</enrollmentCount>
      </college>
      <college>
        <collegeId>C</collegeId>
        <studentCount>50</studentCount>
        <courseCount>10</courseCount>
        <enrollmentCount>250</enrollmentCount>
      </college>
    </Summary>
  </data>
</Response>
```

## 6. 学院系统接口

学院系统主要提供给集成服务器调用，用于把选课结果写回原院数据库。

### 6.1 选课写回

集成服务器将学生选课信息写回到原课程所在学院。

- URL：`/internal/v1/enrollments/writeback`
- 方法：`POST`
- 说明：由集成服务器调用，不直接暴露给学生。

#### 请求示例

```http
POST /internal/v1/enrollments/writeback HTTP/1.1
Host: college-a.local
Content-Type: application/xml
Accept: application/xml
```

```xml
<WritebackRequest>
  <meta>
    <sourceCollegeId>C</sourceCollegeId>
    <targetCollegeId>A</targetCollegeId>
    <status>ENROLLED</status>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>C001</cid>
      <score>95</score>
    </choice>
  </choices>
</WritebackRequest>
```

#### 返回示例

```xml
<Response>
  <code>0</code>
  <message>writeback success</message>
  <data>
    <enrollmentId>E202605170001</enrollmentId>
    <collegeId>A</collegeId>
    <status>ENROLLED</status>
  </data>
</Response>
```

### 6.2 退选写回

退选时由集成服务器通知原学院更新选课状态。

- URL：`/internal/v1/enrollments/withdraw`
- 方法：`POST`
- 说明：同步更新原院记录。

#### 请求示例

```http
POST /internal/v1/enrollments/withdraw HTTP/1.1
Host: college-a.local
Content-Type: application/xml
Accept: application/xml
```

```xml
<WithdrawWritebackRequest>
  <enrollmentId>E202605170001</enrollmentId>
  <studentId>S2024001</studentId>
  <courseId>C001</courseId>
  <status>WITHDRAWN</status>
</WithdrawWritebackRequest>
```

#### 返回示例

```xml
<Response>
  <code>0</code>
  <message>withdraw writeback success</message>
  <data>
    <enrollmentId>E202605170001</enrollmentId>
    <status>WITHDRAWN</status>
  </data>
</Response>
```

## 7. 联调流程说明

### 7.1 共享课程查询流程

1. 学院系统登录后，请求集成服务器的共享课程列表。
2. 集成服务器汇总三院共享课程后返回。
3. 学院系统展示课程列表给学生。

### 7.2 跨院选课流程

1. 学生在学院系统中选择共享课程。
2. 学院系统把选课请求发送给集成服务器。
3. 集成服务器生成选课记录编号，并确认目标学院。
4. 集成服务器调用原课程所在学院的写回接口。
5. 原学院更新数据后返回结果。
6. 集成服务器将最终结果返回给发起学院系统。

### 7.3 退选流程

1. 学生在学院系统发起退选。
2. 学院系统将退选请求发给集成服务器。
3. 集成服务器找到对应选课记录与原学院。
4. 集成服务器调用原学院退选写回接口。
5. 原学院更新状态后返回结果。
6. 集成服务器向前端返回退选完成结果。

### 7.4 统计流程

1. 集成服务器定时或按需汇总三院数据。
2. 统计结果通过 `/api/v1/stats/summary` 返回。
3. 管理端或报告页面直接展示统计结果。

## 8. 联调时的检查点

- 学院系统是否能正确请求共享课程列表。
- 选课请求是否能正确生成 `enrollmentId`。
- 集成服务器是否能正确调用目标学院的写回接口。
- 退选流程是否能把状态同步回原学院。
- 统计接口是否能反映三院数据总量。

## 9. 建议的联调顺序

1. 先调通共享课程查询接口。
2. 再调通跨院选课接口。
3. 再调通写回接口。
4. 再调通退选接口。
5. 最后调通统计接口。

## 10. 备注

- 这里的接口协议是作业实现的基础版本，重点是让四个系统的职责清晰、流程完整、演示可控。
- 后续如果进入编码阶段，可以在不改变业务含义的前提下，把这些接口进一步整理成正式的代码接口。
