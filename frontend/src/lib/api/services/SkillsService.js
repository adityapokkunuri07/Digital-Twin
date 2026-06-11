import { ApiClient } from '../client';

export const SkillsService = {
  getSkills: () => ApiClient.get('/admin/skills'),
  getAdminSkills: () => ApiClient.get('/admin/skills'),
  toggleSkill: (skillId) => ApiClient.post(`/admin/skills/${skillId}/toggle`),
  executeSkill: (skillId, payload) => ApiClient.post(`/skills/execute/${skillId}`, payload),
  getLogs: () => ApiClient.get('/admin/logs')
};
