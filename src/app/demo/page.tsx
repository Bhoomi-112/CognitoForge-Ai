'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ToastContainer, useToast } from '@/components/ui/toast';
import { LatestReport } from '@/components/reports';
import { uploadRepository, simulateAttack, fetchLatestReport, runCompleteAnalysis, healthCheck } from '@/lib/api';
import { validateRepoUrl, validateAnalysisType, combineValidationResults } from '@/lib/validation';
import {
  Shield,
  GitBranch,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Download,
  RefreshCw,
  Play,
  Loader2,
  ArrowLeft,
  Code,
  Database,
  Lock
} from 'lucide-react';
import Link from 'next/link';

interface AnalysisStep {
  id: string;
  message: string;
  status: 'pending' | 'running' | 'complete';
  duration: number;
}

interface Vulnerability {
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  cve?: string;
}

function DemoHeader() {
  return (
    <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold gradient-text">
              CognitoForge
            </Link>
            <div className="h-6 w-px bg-border/40" />
            <span className="text-muted-foreground">Security Analysis Demo</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function RepoInputForm({ onSubmit, isLoading }: { 
  onSubmit: (repoUrl: string, analysisType: string) => void; 
  isLoading: boolean;
}) {
  const [repoUrl, setRepoUrl] = useState('https://github.com/vulnerable-app/node-express-demo');
  const [analysisType, setAnalysisType] = useState('comprehensive');
  const [errors, setErrors] = useState<string[]>([]);
  const [touched, setTouched] = useState({ repoUrl: false, analysisType: false });

  const validateForm = () => {
    const repoValidation = validateRepoUrl(repoUrl);
    const analysisValidation = validateAnalysisType(analysisType);
    const combined = combineValidationResults(repoValidation, analysisValidation);
    
    setErrors(combined.errors);
    return combined.isValid;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched({ repoUrl: true, analysisType: true });
    
    if (validateForm()) {
      onSubmit(repoUrl, analysisType);
    }
  };

  const handleRepoUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRepoUrl(e.target.value);
    if (touched.repoUrl) {
      validateForm();
    }
  };

  const handleAnalysisTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setAnalysisType(e.target.value);
    if (touched.analysisType) {
      validateForm();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto"
    >
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-4">
          AI <span className="gradient-text">Security Analysis</span>
        </h1>
        <p className="text-muted-foreground">
          Enter a repository URL to simulate an AI-powered red team analysis
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 glass p-8 rounded-lg">
        {errors.length > 0 && (
          <div className="bg-red-900/20 border border-red-700/50 text-red-300 px-4 py-3 rounded-lg">
            <ul className="text-sm space-y-1">
              {errors.map((error, index) => (
                <li key={index}>• {error}</li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <label htmlFor="repoUrl" className="block text-sm font-medium mb-2">
            Repository URL
          </label>
          <input
            id="repoUrl"
            type="url"
            value={repoUrl}
            onChange={handleRepoUrlChange}
            onBlur={() => setTouched(prev => ({ ...prev, repoUrl: true }))}
            className={`w-full px-4 py-3 bg-background border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-colors ${
              touched.repoUrl && errors.some(e => e.includes('Repository URL')) 
                ? 'border-red-500' 
                : 'border-border'
            }`}
            placeholder="https://github.com/username/repository"
            required
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="analysisType" className="block text-sm font-medium mb-2">
            Analysis Type
          </label>
          <select
            id="analysisType"
            value={analysisType}
            onChange={handleAnalysisTypeChange}
            onBlur={() => setTouched(prev => ({ ...prev, analysisType: true }))}
            className={`w-full px-4 py-3 bg-background border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-colors ${
              touched.analysisType && errors.some(e => e.includes('Analysis type')) 
                ? 'border-red-500' 
                : 'border-border'
            }`}
            required
            disabled={isLoading}
          >
            <option value="comprehensive">Comprehensive Security Audit</option>
            <option value="quick">Quick Vulnerability Scan</option>
            <option value="cicd">CI/CD Pipeline Analysis</option>
            <option value="dependencies">Dependency Security Check</option>
          </select>
        </div>

        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={isLoading || errors.length > 0}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Initializing Analysis...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              Start Security Analysis
            </>
          )}
        </Button>
      </form>
    </motion.div>
  );
}

function AnalysisProgress({ 
  steps, 
  progress 
}: { 
  steps: AnalysisStep[]; 
  progress: number; 
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto"
    >
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-4">
          Analysis <span className="gradient-text">In Progress</span>
        </h1>
        <p className="text-muted-foreground">
          AI is analyzing your repository for security vulnerabilities
        </p>
      </div>

      {/* Progress Bar */}
      <div className="glass p-6 rounded-lg mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Overall Progress</span>
          <span className="text-sm text-muted-foreground">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-muted rounded-full h-3">
          <motion.div
            className="bg-brand-gradient h-3 rounded-full"
            style={{ width: `${progress}%` }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Analysis Steps */}
      <div className="glass p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Analysis Steps</h3>
        <div className="space-y-3">
          {steps.map((step, index) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-3 p-3 rounded-lg border border-border/40"
            >
              <div className="flex-shrink-0">
                {step.status === 'complete' && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                {step.status === 'running' && (
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                )}
                {step.status === 'pending' && (
                  <div className="h-5 w-5 rounded-full border-2 border-muted" />
                )}
              </div>
              <span className={`text-sm ${
                step.status === 'complete' ? 'text-foreground' : 'text-muted-foreground'
              }`}>
                {step.message}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function SecurityReport({ 
  onNewAnalysis,
  repoId,
  analysisResult 
}: { 
  onNewAnalysis: () => void;
  repoId?: string | null;
  analysisResult?: any;
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const { showSuccess, showError } = useToast();
  
  // Use real analysis result data if available, otherwise use demo data
  const displayData = analysisResult || {
    summary: {
      overall_severity: 'high',
      critical_steps: 1,
      high_steps: 2,
      medium_steps: 3,
      low_steps: 1,
      affected_files: ['src/auth/login.js', 'config/database.js', 'api/admin.js']
    }
  };

  const vulnerabilities: Vulnerability[] = analysisResult?.plan?.steps ? 
    analysisResult.plan.steps.map((step: any) => ({
      title: step.description || 'Unknown vulnerability',
      severity: (step.severity || 'medium').toLowerCase(),
      description: `Technique ID: ${step.technique_id || 'N/A'}`,
      affectedFiles: step.affected_files || []
    })) : [
      {
        title: "SQL Injection in Login Form",
        severity: "critical",
        description: "Unsanitized user input allows database manipulation",
        cve: "CVE-2023-1234"
      },
      {
        title: "Exposed Admin Panel",
        severity: "high",
        description: "Admin interface accessible without proper authentication",
        cve: "CVE-2023-5678"
      },
      {
        title: "Weak Session Management",
        severity: "medium",
        description: "Session tokens are predictable and not properly invalidated"
      }
    ];

  const riskScore = () => {
    const severity = displayData.summary?.overall_severity || 'medium';
    switch (severity.toLowerCase()) {
      case 'critical': return { score: '9.5/10', color: 'text-red-500', level: 'Critical Risk' };
      case 'high': return { score: '8.5/10', color: 'text-orange-500', level: 'High Risk' };
      case 'medium': return { score: '6.0/10', color: 'text-yellow-500', level: 'Medium Risk' };
      case 'low': return { score: '3.0/10', color: 'text-green-500', level: 'Low Risk' };
      default: return { score: '5.0/10', color: 'text-gray-500', level: 'Unknown Risk' };
    }
  };

  const risk = riskScore();
  
  const totalVulns = (displayData.summary?.critical_steps || 0) + 
                    (displayData.summary?.high_steps || 0) + 
                    (displayData.summary?.medium_steps || 0) + 
                    (displayData.summary?.low_steps || 0) || vulnerabilities.length;

  const handleDownloadReport = async () => {
    setIsDownloading(true);
    try {
      // In a real app, this would call the API
      // const result = await downloadReport('demo-report-id', 'pdf');
      
      // For demo, simulate download
      await new Promise(resolve => setTimeout(resolve, 2000));
      showSuccess('Download Complete', 'Security report downloaded successfully');
    } catch (error) {
      showError('Download Failed', 'Failed to download report');
    } finally {
      setIsDownloading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/20';
      case 'high': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
      case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'low': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      default: return 'text-muted-foreground bg-muted/10 border-muted/20';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto"
    >
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-4">
          Security <span className="gradient-text">Analysis Report</span>
        </h1>
        <p className="text-muted-foreground">
          Comprehensive security analysis completed successfully
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        {/* Risk Score */}
        <div className="glass p-6 rounded-lg text-center">
          <div className={`text-3xl font-bold mb-2 ${risk.color}`}>{risk.score}</div>
          <div className="text-sm text-muted-foreground">Risk Score</div>
          <div className={`text-sm mt-1 ${risk.color}`}>{risk.level}</div>
        </div>

        {/* Vulnerabilities Found */}
        <div className="glass p-6 rounded-lg text-center">
          <div className="text-3xl font-bold text-orange-500 mb-2">{totalVulns}</div>
          <div className="text-sm text-muted-foreground">Issues Found</div>
          <div className="text-orange-500 text-sm mt-1">Action Required</div>
        </div>

        {/* Scan Duration */}
        <div className="glass p-6 rounded-lg text-center">
          <div className="text-3xl font-bold text-primary mb-2">
            {analysisResult ? '3.2m' : '2.3m'}
          </div>
          <div className="text-sm text-muted-foreground">Scan Duration</div>
          <div className="text-green-500 text-sm mt-1">Completed</div>
        </div>
      </div>

      {/* Vulnerabilities List */}
      <div className="glass p-6 rounded-lg mb-6">
        <h3 className="text-lg font-semibold mb-4">Discovered Vulnerabilities</h3>
        <div className="space-y-4">
          {vulnerabilities.map((vuln, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-4 border border-border/40 rounded-lg"
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium">{vuln.title}</h4>
                <span className={`px-2 py-1 rounded text-xs border ${getSeverityColor(vuln.severity)}`}>
                  {(vuln.severity || 'unknown').toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-2">{vuln.description}</p>
              {vuln.cve && (
                <span className="text-xs text-muted-foreground">{vuln.cve}</span>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Latest Report Section */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4">Latest Simulation Report</h3>
        <LatestReport repoId={repoId || "demo-repo-123"} />
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button variant="outline" onClick={onNewAnalysis}>
          <RefreshCw className="mr-2 h-4 w-4" />
          New Analysis
        </Button>
        <Button 
          variant="outline" 
          onClick={handleDownloadReport}
          disabled={isDownloading}
        >
          {isDownloading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Downloading...
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              Download Report
            </>
          )}
        </Button>
      </div>
    </motion.div>
  );
}

type DemoPage = 'input' | 'analysis' | 'report';

// Global flag to prevent multiple health check toasts
let healthCheckToastShown = false;

export default function DemoPage() {
  const [currentPage, setCurrentPage] = useState<DemoPage>('input');
  const [analysisSteps, setAnalysisSteps] = useState<AnalysisStep[]>([]);
  const [progress, setProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [currentRepoId, setCurrentRepoId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const { toasts, closeToast, showSuccess, showError, showInfo } = useToast();

  // Check backend health on component mount (only once)
  useEffect(() => {
    const checkBackendHealth = async () => {
      if (healthCheckToastShown) return; // Exit if already shown globally
      
      try {
        const healthResult = await healthCheck();
        if (healthResult.success) {
          showSuccess('Backend Connected', 'CognitoForge backend is online and ready');
          healthCheckToastShown = true;
        } else {
          showInfo('Demo Mode', 'Backend unavailable - using demo simulation');
          healthCheckToastShown = true;
        }
      } catch (error) {
        showInfo('Demo Mode', 'Backend unavailable - using demo simulation');
        healthCheckToastShown = true;
      }
    };

    checkBackendHealth();
  }, []); // Empty dependency array - run only once on mount

  const startAnalysis = async (repoUrl: string, analysisType: string) => {
    setIsLoading(true);
    setCurrentPage('analysis');
    setProgress(0);
    
    // Generate unique repo ID
    const repoId = `repo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setCurrentRepoId(repoId);
    
    try {
      // First, check if backend is available
      const healthResult = await healthCheck();
      
      if (healthResult.success) {
        showSuccess('Backend Connected', 'Connected to CognitoForge backend successfully');
        
        // Use real backend workflow
        const result = await runCompleteAnalysis(
          repoId,
          repoUrl,
          (step: string, progress: number) => {
            setProgress(progress);
            // Update current step in the UI
            const stepMessage = `${step} (${Math.round(progress)}%)`;
            
            // Initialize steps if not done yet
            if (analysisSteps.length === 0) {
              const steps: AnalysisStep[] = [
                { id: '1', message: 'Uploading repository...', status: 'pending', duration: 1500 },
                { id: '2', message: 'Running security simulation...', status: 'pending', duration: 2000 },
                { id: '3', message: 'Generating report...', status: 'pending', duration: 2500 },
                { id: '4', message: 'Analysis complete!', status: 'pending', duration: 500 }
              ];
              setAnalysisSteps(steps);
            }
            
            // Update step status based on progress
            setAnalysisSteps(prev => {
              const stepIndex = Math.floor((progress / 100) * prev.length);
              return prev.map((s, index) => {
                if (index < stepIndex) return { ...s, status: 'complete' };
                if (index === stepIndex) return { ...s, status: 'running', message: stepMessage };
                return s;
              });
            });
          }
        );
        
        if (result.success) {
          setProgress(100);
          setIsLoading(false);
          setAnalysisResult(result.data); // Store the real backend result
          setCurrentPage('report');
          showSuccess('Analysis Complete', 'Real security analysis completed successfully');
          return;
        } else {
          throw new Error(result.error?.message || 'Backend analysis failed');
        }
      } else {
        throw new Error('Backend health check failed');
      }
    } catch (error) {
      console.error('Backend analysis failed:', error);
      showInfo('Demo Mode', 'Backend unavailable, running simulation...');
      
      // Fallback to demo simulation
      await runDemoSimulation();
    }
  };

  const runDemoSimulation = async () => {
    const steps: AnalysisStep[] = [
      { id: '1', message: 'Authenticating with secure analysis environment...', status: 'pending', duration: 1500 },
      { id: '2', message: 'Cloning repository...', status: 'pending', duration: 2000 },
      { id: '3', message: 'Setting up user-specific sandbox...', status: 'pending', duration: 2500 },
      { id: '4', message: 'Analyzing code structure...', status: 'pending', duration: 2500 },
      { id: '5', message: 'Running static security analysis...', status: 'pending', duration: 4000 },
      { id: '6', message: 'Simulating attack scenarios...', status: 'pending', duration: 5000 },
      { id: '7', message: 'Testing CI/CD pipeline vulnerabilities...', status: 'pending', duration: 3500 },
      { id: '8', message: 'Generating personalized attack paths...', status: 'pending', duration: 2000 },
      { id: '9', message: 'Compiling security report...', status: 'pending', duration: 2000 }
    ];

    setAnalysisSteps(steps);
    
    const totalDuration = steps.reduce((sum, step) => sum + step.duration, 0);
    let elapsed = 0;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      
      // Update step to running
      setAnalysisSteps(prev => prev.map(s => 
        s.id === step.id ? { ...s, status: 'running' } : s
      ));
      
      // Update progress
      setProgress((elapsed / totalDuration) * 100);
      
      // Wait for step duration
      await new Promise(resolve => setTimeout(resolve, step.duration));
      
      // Mark step as complete
      setAnalysisSteps(prev => prev.map(s => 
        s.id === step.id ? { ...s, status: 'complete' } : s
      ));
      
      elapsed += step.duration;
    }

    setProgress(100);
    setIsLoading(false);
    
    // Show report after a brief delay
    setTimeout(() => {
      setCurrentPage('report');
      showSuccess('Analysis Complete', 'Security analysis finished successfully');
    }, 2000);
  };

  const startNewAnalysis = () => {
    setCurrentPage('input');
    setAnalysisSteps([]);
    setProgress(0);
    setIsLoading(false);
    setCurrentRepoId(null);
    setAnalysisResult(null);
    showInfo('New Analysis', 'Ready to analyze another repository');
  };

  return (
    <div className="min-h-screen bg-background">
      <DemoHeader />
      <ToastContainer toasts={toasts} onClose={closeToast} />
      
      <main className="container mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          {currentPage === 'input' && (
            <motion.div
              key="input"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <RepoInputForm onSubmit={startAnalysis} isLoading={isLoading} />
            </motion.div>
          )}
          
          {currentPage === 'analysis' && (
            <motion.div
              key="analysis"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <AnalysisProgress steps={analysisSteps} progress={progress} />
            </motion.div>
          )}
          
          {currentPage === 'report' && (
            <motion.div
              key="report"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <SecurityReport 
                onNewAnalysis={startNewAnalysis} 
                repoId={currentRepoId}
                analysisResult={analysisResult}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}