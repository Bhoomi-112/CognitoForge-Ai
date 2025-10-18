// Demo flow management
class CognitoForgeDemo {
  constructor() {
    this.currentPage = 'repo-input';
    this.analysisId = null;
    this.analysisProgress = 0;
    this.init();
  }

  init() {
    this.bindEvents();
    this.showPage('repo-input');
  }

  bindEvents() {
    // Repository form submission
    const repoForm = document.getElementById('repoForm');
    if (repoForm) {
      repoForm.addEventListener('submit', (e) => this.handleRepoSubmission(e));
    }
  }

  showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.demo-page').forEach(page => {
      page.classList.remove('active');
    });

    // Show target page
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
      targetPage.classList.add('active');
      this.currentPage = pageId;
    }
  }

  async handleRepoSubmission(e) {
    e.preventDefault();
    
    const repoUrl = document.getElementById('repoUrl').value;
    const analysisType = document.getElementById('analysisType').value;
    
    // Show loading state
    this.showLoadingState();
    
    // Generate analysis ID
    this.analysisId = 'analysis_' + Date.now();
    
    // Start analysis simulation
    await this.simulateAnalysis(repoUrl, analysisType);
  }

  showLoadingState() {
    const btnText = document.querySelector('.btn-text');
    const btnLoading = document.querySelector('.btn-loading');
    
    btnText.style.display = 'none';
    btnLoading.style.display = 'flex';
    
    // Transition to analysis page after short delay
    setTimeout(() => {
      this.showPage('analyzing');
      this.startAnalysisSimulation();
    }, 1500);
  }

  async simulateAnalysis(repoUrl, analysisType) {
    // This simulates the backend analysis process
    const steps = [
      { message: 'Cloning repository...', duration: 2000 },
      { message: 'Setting up secure sandbox environment...', duration: 3000 },
      { message: 'Analyzing code structure...', duration: 2500 },
      { message: 'Running static security analysis...', duration: 4000 },
      { message: 'Simulating attack scenarios...', duration: 5000 },
      { message: 'Testing CI/CD pipeline vulnerabilities...', duration: 3500 },
      { message: 'Generating attack paths...', duration: 2000 },
      { message: 'Compiling security report...', duration: 2000 }
    ];

    let totalDuration = steps.reduce((sum, step) => sum + step.duration, 0);
    let elapsed = 0;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      
      // Update progress
      this.updateProgress(step.message, (elapsed / totalDuration) * 100);
      
      // Add log entry
      this.addLogEntry(step.message, 'pending');
      
      // Update test categories
      this.updateTestCategories(i);
      
      await this.delay(step.duration);
      
      // Mark step as complete
      this.completeLogEntry(step.message);
      
      elapsed += step.duration;
    }

    // Complete analysis
    this.updateProgress('Analysis complete!', 100);
    
    // Wait a moment then show report
    setTimeout(() => {
      this.showPage('report');
      this.animateReport();
    }, 2000);
  }

  startAnalysisSimulation() {
    // Initialize progress
    this.updateProgress('Initializing analysis...', 0);
  }

  updateProgress(status, percentage) {
    const progressFill = document.querySelector('.progress-fill');
    const progressStatus = document.getElementById('progress-status');
    const progressPercent = document.getElementById('progress-percent');

    if (progressFill) {
      progressFill.style.width = percentage + '%';
    }
    
    if (progressStatus) {
      progressStatus.textContent = status;
    }
    
    if (progressPercent) {
      progressPercent.textContent = Math.round(percentage) + '%';
    }
  }

  addLogEntry(message, status = 'pending') {
    const statusLog = document.getElementById('statusLog');
    if (!statusLog) return;

    const timestamp = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      minute: '2-digit', 
      second: '2-digit' 
    });

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
      <span class="timestamp">[${timestamp}]</span>
      <span class="message">${message}</span>
      <span class="status ${status}">●</span>
    `;

    statusLog.appendChild(entry);
    statusLog.scrollTop = statusLog.scrollHeight;

    // Store reference for later completion
    entry.dataset.message = message;
  }

  completeLogEntry(message) {
    const statusLog = document.getElementById('statusLog');
    if (!statusLog) return;

    const entries = statusLog.querySelectorAll('.log-entry');
    entries.forEach(entry => {
      if (entry.dataset.message === message) {
        const status = entry.querySelector('.status');
        if (status) {
          status.className = 'status complete';
        }
      }
    });
  }

  updateTestCategories(stepIndex) {
    const categories = document.querySelectorAll('.test-category');
    
    categories.forEach((category, index) => {
      const statusEl = category.querySelector('.category-status');
      if (stepIndex > index + 2) {
        statusEl.textContent = 'Complete';
        statusEl.className = 'category-status complete';
      } else if (stepIndex >= index) {
        statusEl.textContent = 'Running';
        statusEl.className = 'category-status running';
      }
    });
  }

  animateReport() {
    // Animate risk gauge
    const gauge = document.querySelector('.gauge-fill');
    if (gauge) {
      setTimeout(() => {
        gauge.style.transform = 'rotate(260deg)'; // 85% score
      }, 500);
    }

    // Animate timeline steps
    const steps = document.querySelectorAll('.timeline-step');
    steps.forEach((step, index) => {
      setTimeout(() => {
        step.classList.add('completed');
      }, 1000 + (index * 300));
    });
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Mock API simulation for Gemini integration
  async generateAttackPlan(codeSnippet) {
    // This simulates the Gemini API call
    const mockResponse = {
      attackPlan: [
        {
          step: 1,
          title: "Initial Reconnaissance",
          description: "Identified exposed API endpoints and weak authentication",
          technique: "Information Gathering",
          severity: "low"
        },
        {
          step: 2,
          title: "SQL Injection Exploit",
          description: "Exploited user login form to bypass authentication",
          technique: "Injection",
          severity: "critical"
        },
        {
          step: 3,
          title: "Privilege Escalation",
          description: "Gained admin access through exposed admin panel",
          technique: "Privilege Escalation",
          severity: "high"
        },
        {
          step: 4,
          title: "Data Exfiltration",
          description: "Downloaded user database and sensitive configuration files",
          technique: "Data Exfiltration",
          severity: "critical"
        }
      ],
      simulatedLog: `[14:23:01] Starting reconnaissance scan...
[14:23:15] Found login endpoint: /api/auth/login
[14:23:32] Testing SQL injection: admin' OR '1'='1
[14:23:45] ✓ Authentication bypassed - admin access gained
[14:24:01] Enumerating admin panel endpoints...
[14:24:18] ✓ Database dump successful - 10,000 user records extracted`,
      riskScore: 8.5,
      vulnerabilities: [
        {
          title: "SQL Injection in Login Form",
          description: "Unsanitized user input allows database manipulation",
          severity: "critical",
          cve: "CVE-2023-1234"
        },
        {
          title: "Exposed Admin Panel",
          description: "Admin interface accessible without proper authentication",
          severity: "high",
          cve: "CVE-2023-5678"
        },
        {
          title: "Weak Session Management",
          description: "Session tokens are predictable and not properly invalidated",
          severity: "medium",
          cve: "CVE-2023-9012"
        }
      ],
      remediation: [
        {
          priority: "P0",
          title: "Fix SQL Injection",
          description: "Use parameterized queries and input validation",
          link: "#"
        },
        {
          priority: "P1",
          title: "Secure Admin Panel",
          description: "Implement proper authentication and access controls",
          link: "#"
        },
        {
          priority: "P2",
          title: "Improve Session Security",
          description: "Use secure, random session tokens with proper expiration",
          link: "#"
        }
      ]
    };

    // Simulate API delay
    await this.delay(2000);
    return mockResponse;
  }
}

// Global functions for UI interactions
function startNewAnalysis() {
  window.demo.showPage('repo-input');
  
  // Reset form
  const form = document.getElementById('repoForm');
  if (form) {
    form.reset();
    document.getElementById('repoUrl').value = 'https://github.com/vulnerable-app/node-express-demo';
  }
  
  // Reset button state
  const btnText = document.querySelector('.btn-text');
  const btnLoading = document.querySelector('.btn-loading');
  
  if (btnText && btnLoading) {
    btnText.style.display = 'inline';
    btnLoading.style.display = 'none';
  }
}

function downloadReport() {
  // Simulate PDF download
  alert('PDF report would be generated and downloaded here');
}

function scheduleRetest() {
  // Simulate scheduling
  alert('Re-test would be scheduled here');
}

// Initialize demo when page loads
document.addEventListener('DOMContentLoaded', function() {
  window.demo = new CognitoForgeDemo();
});