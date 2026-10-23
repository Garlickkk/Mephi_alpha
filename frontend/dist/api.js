// Replace this adapter with HTTP calls. No actual banking operations occur.
const KEY='alfa-demo-applications-v1';
export const api={
 async listApplications(){try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch{return []}},
 async createApplication(data){const items=await this.listApplications();const item={...data,id:crypto.randomUUID(),status:'submitted',createdAt:new Date().toISOString()};localStorage.setItem(KEY,JSON.stringify([item,...items]));return item},
 async assistant(){return {message:'ИИ-ассистент пока не подключён. Здесь он поможет уточнить цель финансирования и объяснит различия продуктов. Предварительный расчёт доступен на главной странице. Реальные рекомендации появятся после подключения ИИ.'}}
};
