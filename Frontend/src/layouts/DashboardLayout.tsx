import { useState, useEffect } from "react"
import { Outlet } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"
import { Sidebar } from "@/components/navigation/Sidebar"
import { Navbar } from "@/components/navigation/Navbar"
import { Breadcrumb } from "@/components/navigation/Breadcrumb"
import { Footer } from "@/components/layout/Footer"

export function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Lock body scroll when mobile navigation drawer is active
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => {
      document.body.style.overflow = ""
    }
  }, [mobileOpen])

  // Handle escape key to dismiss mobile drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mobileOpen) {
        setMobileOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [mobileOpen])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Workspace Sidebar */}
      <div className="hidden md:flex shrink-0">
        <Sidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed((v) => !v)}
        />
      </div>

      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs md:hidden"
              onClick={() => setMobileOpen(false)}
              aria-hidden="true"
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "tween", duration: 0.2 }}
              className="fixed inset-y-0 left-0 z-50 h-full w-64 max-w-[85vw] shadow-elevation-3 md:hidden flex flex-col bg-surface border-r border-border"
              role="dialog"
              aria-modal="true"
              aria-label="Navigation drawer"
            >
              <div className="relative h-full flex flex-col">
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="absolute right-2.5 top-3.5 z-10 p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  aria-label="Close navigation menu"
                >
                  <X className="h-4 w-4" />
                </button>
                <Sidebar
                  collapsed={false}
                  onToggle={() => {}}
                  mobile
                  onClose={() => setMobileOpen(false)}
                />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Workspace Viewport */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Navbar onMenuClick={() => setMobileOpen(true)} />

        <main className="flex-1 overflow-y-auto flex flex-col min-w-0 bg-background">
          {/* Contextual Breadcrumb Bar */}
          <div className="sticky top-0 z-10 flex items-center h-9 px-4 md:px-6 border-b border-border-subtle bg-surface/80 backdrop-blur-xs shrink-0">
            <Breadcrumb />
          </div>

          {/* Main Page Canvas */}
          <div className="flex-1 p-4 md:p-6 lg:p-8 min-w-0">
            <Outlet />
          </div>

          {/* Global Workspace Footer */}
          <Footer />
        </main>
      </div>
    </div>
  )
}
