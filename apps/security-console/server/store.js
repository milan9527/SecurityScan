import {DynamoDBClient} from '@aws-sdk/client-dynamodb';
import {DynamoDBDocumentClient, GetCommand, PutCommand, QueryCommand} from '@aws-sdk/lib-dynamodb';
import {initial, nowSeconds} from './domain.js';
export const db = DynamoDBDocumentClient.from(new DynamoDBClient({}),{marshallOptions:{removeUndefinedValues:true}});
const TableName = process.env.TABLE_NAME;
export async function get(pk) { return (await db.send(new GetCommand({TableName,Key:{pk},ConsistentRead:true}))).Item; }
export async function put(item) { await db.send(new PutCommand({TableName,Item:item})); }
export async function mutate(fn) {
  for (let attempt=0;attempt<12;attempt++) {
    const current = await get('GPU');
    const old = current || initial();
    const next = await fn(structuredClone(old));
    next.version = old.version+1; next.updatedAt = nowSeconds();
    try {
      await db.send(new PutCommand({TableName,Item:next,ConditionExpression:current?'#v = :v':'attribute_not_exists(pk)',...(current?{ExpressionAttributeNames:{'#v':'version'},ExpressionAttributeValues:{':v':old.version}}:{})}));
      return next;
    } catch(e) { if(e.name !== 'ConditionalCheckFailedException') throw e; }
  }
  throw Object.assign(new Error('状态正在更新，请重试'),{status:409});
}
export async function listJobs(user) {
  const r = await db.send(new QueryCommand({TableName,IndexName:'ByOwner',KeyConditionExpression:'#owner = :o',ExpressionAttributeNames:{'#owner':'owner'},ExpressionAttributeValues:{':o':user},ScanIndexForward:false,Limit:40}));
  return r.Items || [];
}

export async function jobHistory(user, cursor) {
  let key;
  if (cursor) {
    try {
      key = JSON.parse(Buffer.from(cursor, 'base64url').toString());
      if (key.owner !== user || typeof key.pk !== 'string' || !key.pk.startsWith('JOB#') || !Number.isFinite(key.createdAt) || Object.keys(key).length !== 3) throw new Error();
    } catch { throw Object.assign(new Error('无效的历史记录游标'), {status:400}); }
  }
  const r = await db.send(new QueryCommand({TableName,IndexName:'ByOwner',KeyConditionExpression:'#owner = :o',ExpressionAttributeNames:{'#owner':'owner'},ExpressionAttributeValues:{':o':user},ScanIndexForward:false,Limit:40,ExclusiveStartKey:key}));
  return {items:r.Items || [],nextCursor:r.LastEvaluatedKey ? Buffer.from(JSON.stringify(r.LastEvaluatedKey)).toString('base64url') : null};
}
