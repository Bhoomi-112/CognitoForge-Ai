// filepath: c:\workspace\CognitoForge-Ai\src\components\ui\toast.tsx
'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, AlertTriangle, X, Info } from 'lucide-react';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

interface ToastProps {
  toast: Toast;
  onClose: (id: string) => void;
}

export function ToastItem({ toast, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose(toast.id);
    }, toast.duration || 5000);

    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onClose]);

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'error':
        return <AlertTriangle className="h-5 w-5 text-red-400" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-400" />;
    }
  };

  const getStyles = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-green-900/80 border-green-700/50 text-green-100';
      case 'error':
        return 'bg-red-900/80 border-red-700/50 text-red-100';
      case 'info':
        return 'bg-blue-900/80 border-blue-700/50 text-blue-100';
    }
  };

  return (
    <div className={`${getStyles()} border px-4 py-3 rounded-lg backdrop-blur-md flex items-start gap-3 shadow-lg max-w-sm`}>
      {getIcon()}
      <div className="flex-1">
        <p className="text-sm font-medium">{toast.title}</p>
        {toast.message && (
          <p className="text-xs opacity-90 mt-1">{toast.message}</p>
        )}
      </div>
      <button 
        onClick={() => onClose(toast.id)}
        className="opacity-70 hover:opacity-100 transition-opacity"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastContainer({ toasts, onClose }: { toasts: Toast[]; onClose: (id: string) => void }) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  );
}

// Toast hook for easy usage
export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (toast: Omit<Toast, 'id'>) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { ...toast, id }]);
  };

  const closeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const showSuccess = (title: string, message?: string) => {
    showToast({ type: 'success', title, message });
  };

  const showError = (title: string, message?: string) => {
    showToast({ type: 'error', title, message });
  };

  const showInfo = (title: string, message?: string) => {
    showToast({ type: 'info', title, message });
  };

  return {
    toasts,
    showToast,
    closeToast,
    showSuccess,
    showError,
    showInfo,
  };
}