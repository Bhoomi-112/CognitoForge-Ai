// Auth types
export interface User {
  sub: string
  name?: string
  email?: string
  picture?: string
  email_verified?: boolean
}

// Component types
export interface ComponentProps {
  children?: React.ReactNode
  className?: string
}

// Demo types
export interface AnalysisStep {
  id: string
  message: string
  status: 'pending' | 'running' | 'complete'
  duration: number
}

export interface Vulnerability {
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  description: string
  cve?: string
}

export interface AnalysisReport {
  id: string
  repoUrl: string
  analysisType: string
  riskScore: number
  vulnerabilities: Vulnerability[]
  scanDuration: string
  timestamp: Date
}

// UI types
export type ButtonVariant = 
  | 'default' 
  | 'destructive' 
  | 'outline' 
  | 'secondary' 
  | 'ghost' 
  | 'link' 
  | 'brand'

export type ButtonSize = 'default' | 'sm' | 'lg' | 'icon'