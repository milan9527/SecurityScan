"""Generate the deployable CloudFormation template (stdlib only)."""
import json
from pathlib import Path
R={}
def ref(n): return {'Ref':n}
def att(n,a='Arn'): return {'Fn::GetAtt':[n,a]}
def sub(s): return {'Fn::Sub':s}
def add(n,t,p,**kw):
 R[n]={'Type':'AWS::'+t,'Properties':p,'Metadata':{'com.aws.cloudformation.Context':{'why':n,'must':'Required by the Strix demo architecture'}},**kw}
def policy(actions,resources): return {'Effect':'Allow','Action':actions,'Resource':resources}
def role(n,svc,statements,managed=None):
 p={'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':svc},'Action':'sts:AssumeRole'}]}}
 if statements:p['Policies']=[{'PolicyName':'runtime','PolicyDocument':{'Version':'2012-10-17','Statement':statements}}]
 if managed:p['ManagedPolicyArns']=managed
 add(n,'IAM::Role',p)
params={k:{'Type':t,**({'Default':d} if d is not None else {})} for k,t,d in [
 ('VpcId','AWS::EC2::VPC::Id','vpc-06543821591d82596'),('Subnets','List<AWS::EC2::Subnet::Id>','subnet-067474a3e1e0e2ff2,subnet-00d33c83ce7560832'),('GpuInstanceId','String','i-0b33a1d2ee1a2065f'),('GpuSecurityGroup','AWS::EC2::SecurityGroup::Id','sg-0715f5b5ff0bf83c3'),('ApiImage','String',None),('WorkerImage','String',None),('LambdaBucket','String',None),('LambdaKey','String','reaper.zip'),('CloudFrontPrefixList','String',None),('EcsAmi','AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>','/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id'),('AllowedRepos','String','milan9527/AgentcoreShell,milan9527/agentcore-superagent-update'),('AllowedHosts','String','')]}
for n in ['Frontend','Reports']:
 add(n,'S3::Bucket',{'PublicAccessBlockConfiguration':{k:True for k in ['BlockPublicAcls','BlockPublicPolicy','IgnorePublicAcls','RestrictPublicBuckets']},'BucketEncryption':{'ServerSideEncryptionConfiguration':[{'ServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]},'OwnershipControls':{'Rules':[{'ObjectOwnership':'BucketOwnerEnforced'}]}},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('Table','DynamoDB::Table',{'BillingMode':'PAY_PER_REQUEST','AttributeDefinitions':[{'AttributeName':k,'AttributeType':t} for k,t in [('pk','S'),('owner','S'),('createdAt','N')]],'KeySchema':[{'AttributeName':'pk','KeyType':'HASH'}],'GlobalSecondaryIndexes':[{'IndexName':'ByOwner','KeySchema':[{'AttributeName':'owner','KeyType':'HASH'},{'AttributeName':'createdAt','KeyType':'RANGE'}],'Projection':{'ProjectionType':'ALL'}}],'SSESpecification':{'SSEEnabled':True},'PointInTimeRecoverySpecification':{'PointInTimeRecoveryEnabled':True},'TimeToLiveSpecification':{'AttributeName':'expiresAt','Enabled':True}},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('DeadLetter','SQS::Queue',{'FifoQueue':True,'SqsManagedSseEnabled':True})
add('Queue','SQS::Queue',{'FifoQueue':True,'SqsManagedSseEnabled':True,'VisibilityTimeout':120,'RedrivePolicy':{'deadLetterTargetArn':att('DeadLetter'),'maxReceiveCount':3}})
for n in ['ApiLogs','WorkerLogs','ReaperLogs']:add(n,'Logs::LogGroup',{'RetentionInDays':14})
for n in ['AlbSG','ApiSG','WorkerSG']:
 add(n,'EC2::SecurityGroup',{'GroupDescription':n,'VpcId':ref('VpcId'),'SecurityGroupEgress':[{'IpProtocol':'-1','CidrIp':'0.0.0.0/0'}]})
add('AlbIngress','EC2::SecurityGroupIngress',{'GroupId':ref('AlbSG'),'IpProtocol':'tcp','FromPort':80,'ToPort':80,'SourcePrefixListId':ref('CloudFrontPrefixList')})
add('ApiIngress','EC2::SecurityGroupIngress',{'GroupId':ref('ApiSG'),'IpProtocol':'tcp','FromPort':3000,'ToPort':3000,'SourceSecurityGroupId':ref('AlbSG')})
for n in ['Api','Worker']:add(n+'GpuIngress','EC2::SecurityGroupIngress',{'GroupId':ref('GpuSecurityGroup'),'IpProtocol':'tcp','FromPort':8000,'ToPort':8000,'SourceSecurityGroupId':ref(n+'SG')})
add('Alb','ElasticLoadBalancingV2::LoadBalancer',{'Scheme':'internal','Subnets':ref('Subnets'),'SecurityGroups':[ref('AlbSG')],'Type':'application'})
add('Targets','ElasticLoadBalancingV2::TargetGroup',{'VpcId':ref('VpcId'),'Protocol':'HTTP','Port':3000,'TargetType':'ip','HealthCheckPath':'/health','TargetGroupAttributes':[{'Key':'deregistration_delay.timeout_seconds','Value':'30'}]})
add('Listener','ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('Alb'),'Port':80,'Protocol':'HTTP','DefaultActions':[{'Type':'forward','TargetGroupArn':ref('Targets')}]})
add('VpcOrigin','CloudFront::VpcOrigin',{'VpcOriginEndpointConfig':{'Arn':ref('Alb'),'HTTPPort':80,'HTTPSPort':443,'Name':sub('${AWS::StackName}-api'),'OriginProtocolPolicy':'http-only'}},DependsOn=['Listener','AlbIngress'])
add('Oac','CloudFront::OriginAccessControl',{'OriginAccessControlConfig':{'Name':sub('${AWS::StackName}-s3'),'OriginAccessControlOriginType':'s3','SigningBehavior':'always','SigningProtocol':'sigv4'}})
cache='658327ea-f89d-4fab-a63d-7e88639e58f6';nocache='413f160d-6f5f-4f3f-a14c-1f2c1e4dcd89'
# Managed CachingDisabled policy ID.
nocache='4135ea2d-6df8-44a3-9df3-4b5a84be39ad'
add('Distribution','CloudFront::Distribution',{'DistributionConfig':{'Enabled':True,'DefaultRootObject':'index.html','HttpVersion':'http2and3','PriceClass':'PriceClass_200','Origins':[{'Id':'web','DomainName':att('Frontend','RegionalDomainName'),'S3OriginConfig':{'OriginAccessIdentity':''},'OriginAccessControlId':ref('Oac')},{'Id':'api','DomainName':att('Alb','DNSName'),'VpcOriginConfig':{'VpcOriginId':att('VpcOrigin','Id'),'OriginReadTimeout':60}}],'DefaultCacheBehavior':{'TargetOriginId':'web','ViewerProtocolPolicy':'redirect-to-https','CachePolicyId':cache,'Compress':True},'CacheBehaviors':[{'PathPattern':'/api/*','TargetOriginId':'api','ViewerProtocolPolicy':'https-only','AllowedMethods':['GET','HEAD','OPTIONS','PUT','POST','PATCH','DELETE'],'CachePolicyId':nocache,'OriginRequestPolicyId':'b689b0a8-53d0-40ab-baf2-68738e2966ac','Compress':True},{'PathPattern':'/config.json','TargetOriginId':'web','ViewerProtocolPolicy':'redirect-to-https','CachePolicyId':nocache}],'ViewerCertificate':{'CloudFrontDefaultCertificate':True}}})
for n in ['Frontend','Reports']:
 statements=[{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[att(n),sub('${'+n+'.Arn}/*')],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}]
 if n=='Frontend':statements.append({'Effect':'Allow','Principal':{'Service':'cloudfront.amazonaws.com'},'Action':'s3:GetObject','Resource':sub('${Frontend.Arn}/*'),'Condition':{'StringEquals':{'AWS:SourceArn':sub('arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}')}}})
 add(n+'Policy','S3::BucketPolicy',{'Bucket':ref(n),'PolicyDocument':{'Version':'2012-10-17','Statement':statements}})
db=policy(['dynamodb:GetItem','dynamodb:PutItem','dynamodb:Query'],[att('Table'),sub('${Table.Arn}/index/*')]);describe=policy(['ec2:DescribeInstances'],'*')
role('ApiRole','ecs-tasks.amazonaws.com',[db,describe,policy(['sqs:SendMessage'],att('Queue')),policy(['s3:GetObject'],sub('${Reports.Arn}/*'))])
role('WorkerRole','ecs-tasks.amazonaws.com',[db,describe,policy(['sqs:ReceiveMessage','sqs:DeleteMessage','sqs:ChangeMessageVisibility'],att('Queue')),policy(['s3:PutObject'],sub('${Reports.Arn}/*'))])
role('ExecutionRole','ecs-tasks.amazonaws.com',[],['arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'])
role('ReaperRole','lambda.amazonaws.com',[db,describe,policy(['ec2:StartInstances','ec2:StopInstances'],sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:instance/${GpuInstanceId}'))],['arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'])
add('Reaper','Lambda::Function',{'Runtime':'nodejs22.x','Handler':'index.handler','Role':att('ReaperRole'),'Timeout':55,'MemorySize':256,'ReservedConcurrentExecutions':1,'Code':{'S3Bucket':ref('LambdaBucket'),'S3Key':ref('LambdaKey')},'Environment':{'Variables':{'TABLE_NAME':ref('Table'),'GPU_INSTANCE_ID':ref('GpuInstanceId')}}})
add('Schedule','Events::Rule',{'ScheduleExpression':'rate(1 minute)','State':'ENABLED','Targets':[{'Arn':att('Reaper'),'Id':'reconcile'}]})
add('SchedulePermission','Lambda::Permission',{'FunctionName':ref('Reaper'),'Action':'lambda:InvokeFunction','Principal':'events.amazonaws.com','SourceArn':att('Schedule')})
add('Cluster','ECS::Cluster',{})
role('HostRole','ec2.amazonaws.com',[],['arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role','arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'])
add('HostProfile','IAM::InstanceProfile',{'Roles':[ref('HostRole')]})
userdata='''#!/bin/bash
set -eux
mkdir -p /opt/strix-work
echo ECS_CLUSTER=${Cluster} >> /etc/ecs/ecs.config
echo ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST=true >> /etc/ecs/ecs.config
cat > /etc/systemd/system/strix-network.service <<'UNIT'
[Unit]
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'iptables -I DOCKER-USER -d 169.254.169.254/32 -j DROP; iptables -I DOCKER-USER -d 169.254.170.2/32 -j DROP'
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
UNIT
systemctl enable --now strix-network.service
'''
add('WorkerHost','EC2::Instance',{'ImageId':ref('EcsAmi'),'InstanceType':'m7i.xlarge','SubnetId':{'Fn::Select':[0,ref('Subnets')]},'SecurityGroupIds':[ref('WorkerSG')],'IamInstanceProfile':ref('HostProfile'),'MetadataOptions':{'HttpTokens':'required','HttpPutResponseHopLimit':1},'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':100,'VolumeType':'gp3','Encrypted':True}}],'UserData':{'Fn::Base64':sub(userdata)},'Tags':[{'Key':'Name','Value':sub('${AWS::StackName}-worker')} ]})
common={'AWS_REGION':ref('AWS::Region'),'TABLE_NAME':ref('Table'),'GPU_INSTANCE_ID':ref('GpuInstanceId'),'QUEUE_URL':ref('Queue'),'ARTIFACT_BUCKET':ref('Reports')}
for n in ['Api','Worker']:
 env=dict(common)
 if n=='Api':env.update(APP_ORIGIN=sub('https://${Distribution.DomainName}'),ALLOWED_REPOS=ref('AllowedRepos'),ALLOWED_HOSTS=ref('AllowedHosts'))
 c={'Name':n.lower(),'Image':ref(n+'Image'),'Essential':True,'Environment':[{'Name':k,'Value':v} for k,v in env.items()],'LogConfiguration':{'LogDriver':'awslogs','Options':{'awslogs-group':ref(n+'Logs'),'awslogs-region':ref('AWS::Region'),'awslogs-stream-prefix':n.lower()}}}
 p={'ExecutionRoleArn':att('ExecutionRole'),'TaskRoleArn':att(n+'Role'),'NetworkMode':'awsvpc' if n=='Api' else 'host','RequiresCompatibilities':['FARGATE' if n=='Api' else 'EC2'],'Cpu':'512' if n=='Api' else '2048','Memory':'1024' if n=='Api' else '8192','ContainerDefinitions':[c]}
 if n=='Api':c['PortMappings']=[{'ContainerPort':3000}]
 else:
  p['Volumes']=[{'Name':'docker','Host':{'SourcePath':'/var/run/docker.sock'}},{'Name':'work','Host':{'SourcePath':'/opt/strix-work'}}]
  c['MountPoints']=[{'SourceVolume':'docker','ContainerPath':'/var/run/docker.sock'},{'SourceVolume':'work','ContainerPath':'/opt/strix-work'}]
 add(n+'Task','ECS::TaskDefinition',p)
 service={'Cluster':ref('Cluster'),'TaskDefinition':ref(n+'Task'),'DesiredCount':1,'LaunchType':'FARGATE' if n=='Api' else 'EC2','DeploymentConfiguration':{'MaximumPercent':200 if n=='Api' else 100,'MinimumHealthyPercent':100 if n=='Api' else 0}}
 if n=='Api':service.update(NetworkConfiguration={'AwsvpcConfiguration':{'AssignPublicIp':'ENABLED','Subnets':ref('Subnets'),'SecurityGroups':[ref('ApiSG')]}},LoadBalancers=[{'ContainerName':'api','ContainerPort':3000,'TargetGroupArn':ref('Targets')}],HealthCheckGracePeriodSeconds=60)
 add(n+'Service','ECS::Service',service,DependsOn=['Listener'] if n=='Api' else ['WorkerHost'])
outputs={n:{'Value':v} for n,v in {'Url':sub('https://${Distribution.DomainName}'),'FrontendBucket':ref('Frontend'),'DistributionId':ref('Distribution'),'Cluster':ref('Cluster')}.items()}
t={'AWSTemplateFormatVersion':'2010-09-09','Description':'Strix console: S3/OAC, private ALB/ECS, retained Spot GPU lifecycle','Metadata':{'AWSToolsMetrics':{'IaC_Generator':'AWSAgentToolkit','Skill':'aws-cloudformation@3'}},'Parameters':params,'Resources':R,'Outputs':outputs}
Path(__file__).with_name('template.json').write_text(json.dumps(t,indent=2)+'\n')
