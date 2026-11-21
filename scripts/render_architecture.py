"""Render documentation-only AWS-style SVG diagrams (no external assets)."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'reports/glm53-superagent/assets'
ORANGE, PURPLE, GREEN, PINK = '#ed7100', '#8c4fff', '#3f8624', '#c925d1'

class Diagram:
    def __init__(self, key, title, subtitle, height):
        self.key = key
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="{height}" viewBox="0 0 1400 {height}" role="img" aria-labelledby="{key}-title {key}-desc">
<title id="{key}-title">{escape(title)}</title><desc id="{key}-desc">{escape(subtitle)}</desc>
<defs><marker id="{key}-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="none" stroke="#546578"/></marker></defs>
<rect width="1400" height="{height}" fill="white"/>
<rect width="1400" height="100" fill="#232f3e"/>
<path d="M32 78 H1368" stroke="#ff9900" stroke-width="3"/>
<style>text{{font-family:'Noto Sans CJK SC',Arial,'Microsoft YaHei',sans-serif;fill:#232f3e}} .title{{font-size:27px;font-weight:700;fill:white}} .sub{{font-size:15px;fill:#d5dbdb}} .label{{font-size:16px;font-weight:700}} .detail{{font-size:14px;fill:#526273}} .edge{{font-size:13px;fill:#35485d}}</style>''']
        self.text(32, 39, title, 'title'); self.text(32, 65, subtitle, 'sub')
    def text(self, x, y, value, cls='detail'):
        self.parts.append(f'<text x="{x}" y="{y}" class="{cls}">{escape(value)}</text>')
    def group(self, x,y,w,h,label,color='#879596',dash=False):
        dash_attr = 'stroke-dasharray="7 5"' if dash else ''
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-width="1.5" {dash_attr}/>')
        self.text(x+16,y+25,label,'label')
    def box(self,x,y,w,title,lines,color=ORANGE,icon='compute'):
        h=104
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="#fafbfc" stroke="#d5dbdb"/><rect x="{x}" y="{y}" width="5" height="{h}" fill="{color}"/><rect x="{x+14}" y="{y+15}" width="38" height="38" fill="{color}"/>')
        shapes={'compute':'<rect x="10" y="10" width="18" height="18"/><path d="M6 13h4m-4 6h4m-4 6h4m18-12h4m-4 6h4m-4 6h4M13 6v4m6-4v4m6-4v4m-12 18v4m6-4v4m6-4v4"/>','store':'<ellipse cx="19" cy="11" rx="11" ry="4"/><path d="M8 11v17c0 6 22 6 22 0V11M8 19c0 6 22 6 22 0"/>','network':'<path d="M7 11h24M7 19h24M7 27h24M12 7v8m14 0v8m-14 0v8"/>','queue':'<rect x="7" y="8" width="24" height="23"/><path d="M12 14h14m-14 5h14m-14 5h14"/>','lambda':'<path d="M10 9h7l12 22h5M17 12L7 31h7l7-13"/>'}
        self.parts.append(f'<g transform="translate({x+14} {y+15})" fill="none" stroke="white" stroke-width="1.5">{shapes[icon]}</g>')
        self.text(x+64,y+32,title,'label')
        for i,line in enumerate(lines): self.text(x+16,y+70+19*i,line)
    def arrow(self,points,label='',lx=0,ly=0,dash=False):
        dash_attr = 'stroke-dasharray="6 4"' if dash else ''
        self.parts.append(f'<polyline points="{points}" fill="none" stroke="#546578" stroke-width="1.6" marker-end="url(#{self.key}-arrow)" {dash_attr}/>')
        if label: self.text(lx,ly,label,'edge')
    def save(self,name):
        (OUT/name).write_text('\n'.join(self.parts)+ '\n</svg>\n')


def console():
    d=Diagram('console','SecurityScan · 演示应用架构','部署配置快照 · 2026-11-21 · AWS 风格服务配色与示意图标',1210)
    d.box(32,125,250,'用户浏览器',['登录后提交扫描目标','GitHub / Web / API'],PURPLE,'network')
    d.box(365,125,290,'Amazon CloudFront',['HTTPS · /api/* 禁用缓存','静态资源通过 OAC 签名读取'],PURPLE,'network')
    d.arrow('282,175 365,175','HTTPS',300,161)
    d.group(32,255,1336,820,'AWS Cloud · Asia Pacific (Mumbai) / ap-south-1')
    d.box(870,295,300,'Amazon S3 · 前端',['私有 Bucket','静态站点资源'],GREEN,'store')
    d.arrow('655,176 1020,176 1020,295','OAC · SigV4',790,163)
    d.group(55,300,775,605,'VPC · 应用与推理私网',PURPLE)
    d.box(85,365,280,'Application Load Balancer',['Internal ALB','通过 CloudFront VPC Origin 接入'],PURPLE,'network')
    d.arrow('510,229 510,343 225,343 225,365','/api/* · VPC Origin · HTTP:80',525,280)
    d.box(490,365,305,'Amazon ECS · API',['AWS Fargate · 用户名 / 密码','会话 Cookie · 扫描任务 API'])
    d.arrow('365,417 490,417','转发请求',389,402)
    d.box(870,440,300,'Amazon DynamoDB',['用户 / 登录会话 / 扫描任务','GPU 租约与生命周期状态'],PINK,'store')
    d.arrow('795,402 847,402 847,468 870,468','读写状态',853,422)
    d.box(490,555,305,'Amazon ECS · Worker',['EC2 m7i.xlarge · Strix','Docker 工具沙箱 · 执行扫描'])
    d.box(870,585,300,'Amazon SQS · FIFO',['扫描任务队列','Worker 轮询并处理'],PINK,'queue')
    d.arrow('740,469 740,520 815,520 815,565 1202,565 1202,635 1170,635','提交扫描',1060,559)
    d.arrow('870,635 795,635','消费任务',805,619)
    d.box(85,555,280,'Strix 测试工具',['本地仓库分析 / 外部 Web、API 测试','外部目标受 allowlist 约束'],PURPLE,'network')
    d.arrow('490,607 365,607','工具调用',386,592)
    d.box(490,755,305,'Amazon EC2 · Spot GPU',['p6-b200.48xlarge · 8 × B200','GLM-5.3 / SGLang · MTP'])
    d.arrow('642,659 642,755','私网模型调用 · :8000/v1',658,709)
    d.box(870,755,300,'Amazon S3 · 报告',['私有 Bucket · 扫描产物','应用提供授权报告下载'],GREEN,'store')
    d.arrow('795,586 825,586 825,806 870,806','写入报告',835,724)
    d.box(490,950,305,'AWS Lambda',['GPU 生命周期控制','StartInstances / StopInstances'],ORANGE,'lambda')
    d.arrow('642,950 642,859','启动 / 停止',658,929,True)
    d.box(85,950,280,'Amazon EventBridge',['每分钟触发 GPU 生命周期检查'],PINK,'network')
    d.arrow('365,1002 490,1002','定时触发',386,988,True)
    d.text(55,1110,'演示接管后：无活动会话 / 扫描持续 600 秒 → 停止 GPU（不终止实例）。')
    d.text(55,1136,'Lambda 根据 DynamoDB 租约判断；活动扫描保活，浏览器关闭后租约有过期延迟。')
    d.text(55,1162,'GPU 冷启动含模型加载；应用 EC2、API 与 ALB 持续运行。架构图不代表当前资源状态。')
    d.save('console-architecture.svg')


def benchmark():
    d=Diagram('benchmark','SecurityScan · Strix 扫描与性能测试架构','历史测试路径 · 独立流式基准经 SSM 隧道 · EC2 自建 GLM-5.3',720)
    d.group(32,130,480,430,'控制主机 / 测试工作区')
    d.box(60,185,425,'systemd · 后台测试服务',['模型就绪检查 → 流式基准 → Strix deep','进度与证据落盘；不依赖对话连接'])
    d.box(60,335,425,'Strix Agent + Docker',['agentcore-superagent-update · 固定提交','OpenAI-compatible · 127.0.0.1:18000'])
    d.arrow('270,289 270,335')
    d.text(60,495,'产物：JSONL / 扫描发现 / 请求耗时 / 工具调用')
    d.text(60,524,'文档：README + RESULTS.md + 独立 HTML 报告')
    d.group(760,130,605,430,'AWS Cloud · ap-south-1a / Mumbai')
    d.box(790,185,545,'Amazon EC2 · p6-b200.48xlarge',['Persistent Spot · 8 × NVIDIA B200','SGLang 0.5.23 · zai-org/GLM-5.3 · :8000/v1'])
    d.box(790,335,545,'Amazon EBS · 模型存储',['200 GiB 系统盘 + 2048 GiB 模型缓存','容器 glm53-mtp-ablation · /model-cache'],GREEN,'store')
    d.text(790,495,'推理：TP=8 · FP8 KV · context=262144 · max running=2')
    d.text(790,524,'MTP / EAGLE：steps=3 · top-k=1 · draft tokens=4')
    d.arrow('485,385 635,385 635,237 790,237','AWS Systems Manager',535,195)
    d.text(540,217,'SSM 端口转发')
    d.text(535,430,'18000 → 8000')
    d.group(32,590,1333,100,'测量口径与运行边界',GREEN)
    d.text(50,645,'独立流式基准：TTFT / TTOT / E2E / 吞吐。完整 Strix 扫描：非流式延迟与总耗时，无 TTFT。')
    d.text(50,671,'历史测试自动停止禁用；模型端口不直接暴露公网。本图对应测试证据，应用演示的自动停止策略见另一张架构图。')
    d.save('deployment-architecture.svg')

if __name__=='__main__':
    console(); benchmark()
