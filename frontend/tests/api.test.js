import test from 'node:test';import assert from 'node:assert/strict';import {api,normalizeApplication,normalizeProduct} from '../dist/api.js';
test('registration loads the authenticated profile rather than an admin-only login URL',async()=>{
 const calls=[];
 globalThis.fetch=async(path,options)=>{
  calls.push({path,options});
  if(path==='/api/v0/auth/register')return Response.json({accessToken:'registered-access',refreshToken:'registered-refresh'},{status:201});
  if(path==='/api/v0/users/me')return Response.json({login:'client',organizationType:'OOO',firstName:'Иван',lastName:'Иванов',inn:'7700000001',registrationDate:'2020-01-01'});
  return Response.json({message:'Forbidden'},{status:403});
 };
 await api.register({login:'client',password:'password123'});
 const profile=await api.getProfile();
 assert.equal(profile.inn,'7700000001');
 assert.equal(profile.legalForm,'ООО');
 assert.equal(calls[1].path,'/api/v0/users/me');
 assert.equal(calls[1].options.headers.Authorization,'Bearer registered-access');
});
test('expired access token refreshes once before retrying the own-profile endpoint',async()=>{
 const paths=[];
 globalThis.fetch=async(path,options)=>{
  paths.push(path);
  if(path.endsWith('/login'))return Response.json({accessToken:'expired',refreshToken:'refresh'});
  if(path.endsWith('/refresh'))return Response.json({accessToken:'renewed',refreshToken:'next-refresh'});
  if(options.headers.Authorization==='Bearer expired')return new Response(null,{status:401});
  return Response.json({organizationType:'IP',firstName:'Тест',lastName:'Тест',registrationDate:'2020-01-01'});
 };
 await api.login('client','password');
 assert.equal((await api.getProfile()).legalForm,'ИП');
 assert.deepEqual(paths,['/api/v0/auth/login','/api/v0/users/me','/api/v0/auth/refresh','/api/v0/users/me']);
});
test('maps actual backend product bounds and repayment type',()=>{const p=normalizeProduct({id:1,minSum:1000,maxSum:100000,minDurationYear:1,maxDurationYear:5,repaymentTypes:['EQUAL_TOTAL_PARTS']});assert.equal(p.minMonths,12);assert.equal(p.maxMonths,60);assert.equal(p.kind,'annuity')});
test('maps pending and counter-offer without losing original terms',()=>{const p=normalizeApplication({status:'COUNTER_OFFER',amount:1000000,durationYears:2,counterOffer:{amount:500000,durationYears:3,rate:20}});assert.equal(p.requested.amount,1000000);assert.equal(p.decision.amount,500000);assert.equal(p.decision.months,36);assert.equal(normalizeApplication({status:'UNDER_CONSIDERATION',durationYears:1}).decision.status,'pending')});
test('login and create payload follow controllers, no client user_id',async()=>{const calls=[];globalThis.fetch=async(path,options)=>{calls.push({path,options});const body=path.endsWith('/login')?{accessToken:'test-access',refreshToken:'test-refresh'}:path.includes('/users/')?{organizationType:'IP',firstName:'Тест',lastName:'Тест',registrationDate:'2020-01-01'}:{id:1,status:'UNDER_CONSIDERATION',amount:100000,durationYears:2};return new Response(JSON.stringify(body),{status:200})};await api.login('test','password');await api.submitApplication({productId:3,amount:100000,months:24,collateral:false,purpose:'Закупка'});const call=calls.at(-1);assert.equal(call.options.headers.Authorization,'Bearer test-access');assert.deepEqual(JSON.parse(call.options.body),{productId:3,calculator:{amount:100000,durationYears:2,organizationType:'IP',collateral:false,purpose:'Закупка'}})});
