// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/Widget.tsx
'use client'

import {
  Users,
  Mail,
  DollarSign,
  CheckCircle,
  TrendingUp,
  TrendingDown
} from 'lucide-react'

interface WidgetProps {
  title: string
  value: string
  change: string
  icon: keyof typeof IconMap
  trend?: 'up' | 'down' | 'neutral'
}

const IconMap = {
  Users: Users,
  Mail: Mail,
  DollarSign: DollarSign,
  CheckCircle: CheckCircle
} as const

export function Widget({
  title,
  value,
  change,
  icon,
  trend = 'neutral'
}: WidgetProps) {
  const Icon = IconMap[icon]

  const getTrendClass = () => {
    switch (trend) {
      case 'up': return 'text-green-500'
      case 'down': return 'text-red-500'
      default: return 'text-muted-foreground'
    }
  }

  const getTrendIcon = () => {
    switch (trend) {
      case 'up': return <TrendingUp className="h-4 w-4" />
      case 'down': return <TrendingDown className="h-4 w-4" />
      default: return null
    }
  }

  return (
    <div className="bg-card rounded-lg border border-muted/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        <div className="flex items-center gap-2">
          {getTrendIcon()}
          <span className={`text-xs font-medium ${getTrendClass()}`}>{change}</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 flex items-center justify-center bg-primary/10 text-primary rounded-lg">
          <Icon className="h-4 w-4" />
        </div>
        <p className="text-2xl font-semibold text-foreground">{value}</p>
      </div>
    </div>
  )
}