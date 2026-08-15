---
title: Dragonfly 抓取：Personal Access Tokens
date: 2026-09-14 09:42:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/personal-access-tokens/>

---

You can use a personal access token to call open API.

In this article, you will learn how to create, use, modify and delete personal access token.

## About personal access tokens

Only users with
root
role can list all personal access tokens.

## Create personal access token

Click the
ADD PERSONAL ACCESS TOKENS
button to create personal access token.

Name
: Set your token a descriptive name.

Description
: Set a description.

Expiration
: Set your token an expiration.

Scopes
: Select the access permissions for the token.

Click
SAVE
and copy the token and store it. For your security, it doesn't display again.

## Update personal access token

Click
personal access token name
and update your personal access token.

## Delete personal access token

Click
DELETE
and delete your personal access token.

## Use personal access token

### Add personal access token to Authorization header

Step 1:
Open Postman, and import
postman_collection.json
.

Step 2:
Click
Open API
in the sidebar.

Step 3:
Click
Authorization
and select
Bearer Token
, paste
personal access token
in
Token
.

Step 4:
Click
Headers
, check whether
Authorization
is added to Headers.

Step 5:
Click
Send
button to initiate a request.

Step 6:
If successful, it means that the call to the open API is completed through the personal access token.

### Add personal access token to URL query parameter

Step 1:
Open Postman, and import
postman_collection.json
.

Step 2:
Click
Open API
in the sidebar.

Step 3:
Add
access_token=your_personal_access_token
to URL query parameter.

Step 4:
Click
Send
button to initiate a request.

Step 5:
If successful, it means that the call to the open API is completed through the personal access token.

---

> 完整与最新内容以官方文档为准：[Personal Access Tokens](https://d7y.io/docs/next/advanced-guides/personal-access-tokens/)
