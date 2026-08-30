# 媒体溯源、元数据与 C2PA 的使用边界

## 元数据应如何使用

文件名、创建时间、编码器、分辨率、码率和容器信息可以帮助重建处理链，但它们可能在转发、导出或编辑中被删除或改写。因此，元数据适合作为取证线索，不能单独证明内容真实或伪造。应尽量保留原始文件、下载方式、文件哈希和处理记录。

## C2PA / Content Credentials 能提供什么

C2PA Content Credentials 用可验证的声明、内容绑定和签名记录资产的来源与编辑历史。有效凭证可提供溯源证据；缺少凭证不代表内容就是伪造，因为 C2PA 是可选生态且凭证可能因平台处理而不可获得。平台应把“凭证校验结果”和“模型检测结果”分别展示，避免把二者混为同一个真实性结论。

## 对平台问答的结论

当用户问“元数据能否证明真假”时，应回答：元数据与内容凭证可支持来源核验和过程追溯，但需要结合原始文件、签名/信任链校验、媒体取证和模型检测，不能替代交叉验证。

## 参考资料

- C2PA Content Credentials Specification 2.4，https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html。
- 项目本地资料 `knowledge-base/external/c2pa-content-credentials-explainer-2025.pdf`。
