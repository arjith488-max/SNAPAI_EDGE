import React, { forwardRef } from 'react'

// ── Bubble Card ──────────────────────────────────────────────────
export interface BubbleCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'glass' | 'elevated' | 'subtle' | 'gradient'
  interactive?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
  glow?: boolean
}

export const BubbleCard = forwardRef<HTMLDivElement, BubbleCardProps>(
  ({ variant = 'glass', interactive = false, size = 'md', glow = false, className = '', children, ...props }, ref) => {
    const classes = [
      'bubble-card',
      `bubble-card-${variant}`,
      `bubble-card-${size}`,
      interactive ? 'bubble-card-interactive' : '',
      glow ? 'bubble-card-glow' : '',
      className,
    ].filter(Boolean).join(' ')

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    )
  }
)
BubbleCard.displayName = 'BubbleCard'

// ── Bubble Button ────────────────────────────────────────────────
export interface BubbleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'glass' | 'danger' | 'glow'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'icon-sm' | 'icon-md' | 'icon-lg'
  active?: boolean
  pill?: boolean
}

export const BubbleButton = forwardRef<HTMLButtonElement, BubbleButtonProps>(
  ({ variant = 'glass', size = 'md', active = false, pill = false, className = '', children, ...props }, ref) => {
    const classes = [
      'bubble-btn',
      `bubble-btn-${variant}`,
      `bubble-btn-${size}`,
      active ? 'active' : '',
      pill ? 'bubble-btn-pill' : '',
      className,
    ].filter(Boolean).join(' ')

    return (
      <button ref={ref} className={classes} {...props}>
        {children}
      </button>
    )
  }
)
BubbleButton.displayName = 'BubbleButton'

// ── Bubble Badge ─────────────────────────────────────────────────
export interface BubbleBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'local' | 'cloud' | 'hybrid' | 'offline' | 'brand' | 'success' | 'warning' | 'error' | 'neutral'
  pulse?: boolean
  size?: 'sm' | 'md'
}

export const BubbleBadge: React.FC<BubbleBadgeProps> = ({
  variant = 'neutral',
  pulse = false,
  size = 'sm',
  className = '',
  children,
  ...props
}) => {
  return (
    <span className={`bubble-badge bubble-badge-${variant} bubble-badge-${size} ${pulse ? 'pulse' : ''} ${className}`} {...props}>
      {children}
    </span>
  )
}

// ── Bubble Status ────────────────────────────────────────────────
export interface BubbleStatusProps {
  mode: 'local' | 'cloud' | 'hybrid' | 'offline' | string
  label?: string
  sublabel?: string
  onClick?: () => void
  className?: string
}

export const BubbleStatus: React.FC<BubbleStatusProps> = ({ mode, label, sublabel, onClick, className = '' }) => {
  const m = mode.toLowerCase()
  const iconMap: Record<string, string> = {
    local: '⚡',
    cloud: '☁',
    hybrid: '◐',
    offline: '○',
  }
  const defaultLabelMap: Record<string, string> = {
    local: 'LOCAL',
    cloud: 'CLOUD',
    hybrid: 'HYBRID',
    offline: 'OFFLINE',
  }

  return (
    <div
      className={`bubble-status bubble-status-${m} ${onClick ? 'clickable' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <span className={`bubble-dot bubble-dot-${m}`} />
      <div className="bubble-status-content">
        <span className="bubble-status-title">
          <span className="bubble-status-icon">{iconMap[m] || '●'}</span>
          {label || defaultLabelMap[m] || mode.toUpperCase()}
        </span>
        {sublabel && <span className="bubble-status-sub">{sublabel}</span>}
      </div>
    </div>
  )
}

// ── Bubble Avatar ────────────────────────────────────────────────
export interface BubbleAvatarProps {
  type: 'ai' | 'user' | 'system'
  icon?: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export const BubbleAvatar: React.FC<BubbleAvatarProps> = ({ type, icon, size = 'md', className = '' }) => {
  return (
    <div className={`bubble-avatar bubble-avatar-${type} bubble-avatar-${size} ${className}`}>
      {icon ? icon : type === 'ai' ? 'S' : type === 'user' ? '👤' : '⚡'}
    </div>
  )
}

// ── Bubble Icon Container ────────────────────────────────────────
export interface BubbleIconProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg'
  glow?: boolean
}

export const BubbleIcon: React.FC<BubbleIconProps> = ({ size = 'md', glow = false, className = '', children, ...props }) => {
  return (
    <div className={`bubble-icon bubble-icon-${size} ${glow ? 'bubble-icon-glow' : ''} ${className}`} {...props}>
      {children}
    </div>
  )
}

// ── Bubble Modal ─────────────────────────────────────────────────
export interface BubbleModalProps {
  open: boolean
  onClose: () => void
  title?: string
  icon?: string
  children: React.ReactNode
  maxWidth?: number | string
}

export const BubbleModal: React.FC<BubbleModalProps> = ({
  open,
  onClose,
  title,
  icon,
  children,
  maxWidth = 520,
}) => {
  if (!open) return null

  return (
    <div className="bubble-modal-backdrop" onClick={onClose}>
      <div
        className="bubble-modal-content"
        style={{ maxWidth }}
        onClick={e => e.stopPropagation()}
      >
        {title && (
          <div className="bubble-modal-header">
            {icon && <span className="bubble-modal-icon">{icon}</span>}
            <h3 className="bubble-modal-title">{title}</h3>
            <button className="bubble-modal-close" onClick={onClose} aria-label="Close modal">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        <div className="bubble-modal-body">{children}</div>
      </div>
    </div>
  )
}
