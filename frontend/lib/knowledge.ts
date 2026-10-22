// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/lib/knowledge.ts

const DEPARTMENT_LABELS: Record<string, string> = {
  ceo: 'CEO',
  programs_manager: 'Program Management',
  customer_success: 'Customer Success',
  business_support: 'Business Support',
  executive_assistant: 'Executive Assistant',
  enrollment: 'Sales & Enrollment',
  developer: 'Platform Engineering',
  marketing: 'Marketing',
  marketing_lead: 'Marketing Lead',
  graphic_designer: 'Graphic & Funnel Designer',
  sales: 'Sales',
  videographer: 'Videographer',
}

export function departmentLabel(department: string): string {
  return DEPARTMENT_LABELS[department] ?? department.replaceAll('_', ' ')
}
