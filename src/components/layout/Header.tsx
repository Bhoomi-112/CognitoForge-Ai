'use client'

import Link from 'next/link'
import { AuthButton } from '@/components/auth/auth-components'
import { useUser } from '@auth0/nextjs-auth0/client'

interface HeaderProps {
  variant?: 'default' | 'demo'
}

export function Header({ variant = 'default' }: HeaderProps) {
  const { user } = useUser()

  return (
    <header className="fixed top-0 w-full z-50 glass border-b border-border/40">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold gradient-text">
              CognitoForge
            </Link>
            {variant === 'demo' && (
              <>
                <div className="h-6 w-px bg-border/40" />
                <span className="text-muted-foreground">Security Analysis</span>
              </>
            )}
          </div>
          
          <nav className="hidden md:flex items-center space-x-8">
            <Link 
              href="#features" 
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Features
            </Link>
            <Link 
              href="/demo" 
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Demo
            </Link>
            
            {user && (
              <div className="flex items-center gap-3">
                <img
                  src={user.picture}
                  alt={user.name || 'User'}
                  className="h-8 w-8 rounded-full border border-border"
                />
                <span className="text-sm font-medium">{user.name}</span>
              </div>
            )}
            
            <AuthButton />
          </nav>
        </div>
      </div>
    </header>
  )
}