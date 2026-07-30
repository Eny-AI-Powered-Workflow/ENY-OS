// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/page.tsx
import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-background to-primary/5 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left side - Content */}
            <div className="space-y-8">
              <h1 className="text-5xl font-bold text-foreground mb-4 text-center md:text-left">
                <span className="block mb-2">ENY Consulting Platform</span>
                <span className="block text-accent">AI-Powered Enterprise Transformation</span>
              </h1>

              <p className="text-xl text-muted-foreground max-w-2xl text-center md:text-left leading-relaxed">
                Unlock your organization's full potential with our unified AI-powered platform.
                Streamline operations, enhance decision-making, and drive innovation across every department
                through intelligent automation and role-based access control.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center md:justify-start">
                <Link
                  href="/login"
                  className="flex-1 sm:w-auto px-6 py-3 btn-accent hover:bg-accent/90 transition-all font-medium text-center md:text-left"
                >
                  Get Started → Sign In
                </Link>
                <Link
                  href="/dashboard"
                  className="flex-1 sm:w-auto px-6 py-3 btn-outline border-accent/50 hover:bg-accent/10"
                >
                  Explore Dashboard
                </Link>
              </div>
            </div>

            {/* Right side - Illustration or Visual */}
            <div className="relative">
              <div className="absolute -inset-2 border-2 border-accent/20 opacity-20"></div>
              <div className="relative z-10 rounded-xl overflow-hidden shadow-2xl bg-white/5 backdrop-blur-md border border-white/10">
                {/* Abstract geometric pattern representing interconnected systems */}
                <div className="h-96 bg-gradient-to-br from-primary/5 to-transparent">
                  <div className="grid h-full gap-2" style={{ gridTemplateRows: 'repeat(12, 1fr)' }}>
                    <div className="col-span-12 bg-accent/10"></div>
                    <div className="col-span-6 bg-primary/10"></div>
                    <div className="col-span-6 bg-accent/10"></div>
                    <div className="col-span-4 bg-accent/10"></div>
                    <div className="col-span-8 bg-primary/10"></div>
                    <div className="col-span-6 bg-accent/20"></div>
                    <div className="col-span-6 bg-accent/15"></div>
                    <div className="col-span-3 bg-primary/10"></div>
                    <div className="col-span-9 bg-accent/5"></div>
                    <div className="col-span-12 bg-accent/8"></div>
                    <div className="col-span-5 bg-primary/12"></div>
                    <div className="col-span-7 bg-accent/8"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Floating decorative elements */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -top-10 left-1/2 -translate-x-1/2 w-20 h-20 bg-accent/10 rounded-full"></div>
          <div className="absolute bottom-10 right-1/2 -translate-x-1/2 w-16 h-16 bg-primary/10 rounded-full"></div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-background">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-foreground mb-12">
            Platform Capabilities
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature Card 1: Unified Platform */}
            <div className="bg-card/50 backdrop-blur-sm rounded-2xl p-8 border border-border/50 hover:border-border/70 transition-all hover:shadow-lg">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-accent/10 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 2a.5.5 0 100-1 .5.5 0 000 1zm0 7c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-4a.5.5 0 100-1 .5.5 0 000 1z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">Unified Platform</h3>
                  <p className="text-muted-foreground">
                    One login, one interface, unified access to all department-specific tools and agents.
                    No more juggling multiple systems or passwords.
                  </p>
                </div>
              </div>
            </div>

            {/* Feature Card 2: AI-Powered Agents */}
            <div className="bg-card/50 backdrop-blur-sm rounded-2xl p-8 border border-border/50 hover:border-border/70 transition-all hover:shadow-lg">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-accent/10 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 2a.5.5 0 100-1 .5.5 0 000 1zm0 7c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-4a.5.5 0 100-1 .5.5 0 000 1z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">AI-Powered Agents</h3>
                  <p className="text-muted-foreground">
                    Leverage department-specific AI agents powered by Claude for intelligent automation,
                    insights generation, and decision support tailored to your role.
                  </p>
                </div>
              </div>
            </div>

            {/* Feature Card 3: Role-Based Security */}
            <div className="bg-card/50 backdrop-blur-sm rounded-2xl p-8 border border-border/50 hover:border-border/70 transition-all hover:shadow-lg">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-accent/10 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 2a.5.5 0 100-1 .5.5 0 000 1zm0 7c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-4a.5.5 0 100-1 .5.5 0 000 1z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">Enterprise Security</h3>
                  <p className="text-muted-foreground">
                    Robust role-based access control ensures users only see what they're authorized to access,
                    with comprehensive audit logging for compliance and security.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20 bg-muted/50">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-foreground mb-12">
            How It Works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="flex flex-col items-center text-center space-y-6">
              <div className="w-14 h-14 flex-shrink-0 bg-accent/10 rounded-xl flex items-center justify-center">
                <span className="text-2xl font-bold text-accent">1</span>
              </div>
              <h3 className="text-xl font-semibold text-foreground">Login & Authentication</h3>
              <p className="text-muted-foreground max-w-md">
                Secure sign-in with role-based permissions determining your access to modules and data.
              </p>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center text-center space-y-6">
              <div className="w-14 h-14 flex-shrink-0 bg-accent/10 rounded-xl flex items-center justify-center">
                <span className="text-2xl font-bold text-accent">2</span>
              </div>
              <h3 className="text-xl font-semibold text-foreground">Access Your Modules</h3>
              <p className="text-muted-foreground max-w-md">
                Navigate to your authorized modules like CEO Cockpit, Sales & Enrollment, or Student Success.
              </p>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center text-center space-y-6">
              <div className="w-14 h-14 flex-shrink-0 bg-accent/10 rounded-xl flex items-center justify-center">
                <span className="text-2xl font-bold text-accent">3</span>
              </div>
              <h3 className="text-xl font-semibold text-foreground">Leverage AI Agents</h3>
              <p className="text-muted-foreground max-w-md">
                Launch specialized AI agents to automate tasks, generate reports, and gain insights.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-24 bg-gradient-to-r from-primary to-primary/90">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-primary-foreground mb-6">
            Ready to Transform Your Organization?
          </h2>
          <p className="text-xl text-primary-foreground/80 mb-8 max-w-2xl mx-auto">
            Join the future of enterprise operations with AI-powered efficiency and unified access.
          </p>
          <Link
            href="/login"
            className="inline-block px-8 py-4 bg-accent text-accent-foreground hover:bg-accent/90 transition-all font-semibold rounded-lg shadow-md"
          >
            Get Started Today
          </Link>
        </div>
      </section>
    </main>
  )
}