/**
 * Touch gesture utilities for mobile interactions
 */
import React from 'react';

export interface TouchPoint {
    x: number;
    y: number;
    timestamp: number;
}

export interface SwipeGesture {
    direction: 'left' | 'right' | 'up' | 'down';
    distance: number;
    duration: number;
    velocity: number;
}

export interface PinchGesture {
    scale: number;
    center: TouchPoint;
    distance: number;
}

export interface TapGesture {
    x: number;
    y: number;
    timestamp: number;
    isDoubleTap: boolean;
}

export type GestureCallback<T> = (gesture: T) => void;

export class TouchGestureRecognizer {
    private element: HTMLElement;
    private touchStart: TouchPoint[] = [];
    private touchCurrent: TouchPoint[] = [];
    private lastTap: TouchPoint | null = null;
    private doubleTapTimeout: NodeJS.Timeout | null = null;

    // Configuration
    private config = {
        swipeThreshold: 50, // Minimum distance for swipe
        swipeTimeout: 300, // Maximum time for swipe
        doubleTapDelay: 300, // Maximum time between taps for double tap
        doubleTapDistance: 30, // Maximum distance between taps for double tap
        pinchThreshold: 10, // Minimum distance change for pinch
    };

    // Callbacks
    private onSwipe: GestureCallback<SwipeGesture> | null = null;
    private onPinch: GestureCallback<PinchGesture> | null = null;
    private onTap: GestureCallback<TapGesture> | null = null;
    private onDoubleTap: GestureCallback<TapGesture> | null = null;

    constructor(element: HTMLElement, config?: Partial<typeof this.config>) {
        this.element = element;
        this.config = { ...this.config, ...config };
        this.setupEventListeners();
    }

    private setupEventListeners(): void {
        // Prevent default touch behaviors
        this.element.style.touchAction = 'none';

        this.element.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        this.element.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        this.element.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        this.element.addEventListener('touchcancel', this.handleTouchCancel.bind(this), { passive: false });
    }

    private handleTouchStart(event: TouchEvent): void {
        event.preventDefault();

        this.touchStart = Array.from(event.touches).map(touch => ({
            x: touch.clientX,
            y: touch.clientY,
            timestamp: Date.now(),
        }));

        this.touchCurrent = [...this.touchStart];
    }

    private handleTouchMove(event: TouchEvent): void {
        event.preventDefault();

        this.touchCurrent = Array.from(event.touches).map(touch => ({
            x: touch.clientX,
            y: touch.clientY,
            timestamp: Date.now(),
        }));

        // Handle pinch gesture
        if (this.touchStart.length === 2 && this.touchCurrent.length === 2) {
            this.handlePinchGesture();
        }
    }

    private handleTouchEnd(event: TouchEvent): void {
        event.preventDefault();

        const touchEnd = Array.from(event.changedTouches).map(touch => ({
            x: touch.clientX,
            y: touch.clientY,
            timestamp: Date.now(),
        }));

        // Handle single finger gestures
        if (this.touchStart.length === 1 && touchEnd.length === 1) {
            const start = this.touchStart[0];
            const end = touchEnd[0];

            const distance = this.calculateDistance(start, end);
            const duration = end.timestamp - start.timestamp;

            if (distance < this.config.swipeThreshold && duration < this.config.swipeTimeout) {
                // Tap gesture
                this.handleTapGesture(end);
            } else if (distance >= this.config.swipeThreshold && duration <= this.config.swipeTimeout) {
                // Swipe gesture
                this.handleSwipeGesture(start, end, duration);
            }
        }

        // Reset touch points
        this.touchStart = [];
        this.touchCurrent = [];
    }

    private handleTouchCancel(event: TouchEvent): void {
        event.preventDefault();
        this.touchStart = [];
        this.touchCurrent = [];
    }

    private handleSwipeGesture(start: TouchPoint, end: TouchPoint, duration: number): void {
        if (!this.onSwipe) return;

        const deltaX = end.x - start.x;
        const deltaY = end.y - start.y;
        const distance = this.calculateDistance(start, end);
        const velocity = distance / duration;

        let direction: SwipeGesture['direction'];

        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            direction = deltaX > 0 ? 'right' : 'left';
        } else {
            direction = deltaY > 0 ? 'down' : 'up';
        }

        this.onSwipe({
            direction,
            distance,
            duration,
            velocity,
        });
    }

    private handlePinchGesture(): void {
        if (!this.onPinch || this.touchStart.length !== 2 || this.touchCurrent.length !== 2) return;

        const startDistance = this.calculateDistance(this.touchStart[0], this.touchStart[1]);
        const currentDistance = this.calculateDistance(this.touchCurrent[0], this.touchCurrent[1]);

        if (Math.abs(currentDistance - startDistance) < this.config.pinchThreshold) return;

        const scale = currentDistance / startDistance;
        const center = {
            x: (this.touchCurrent[0].x + this.touchCurrent[1].x) / 2,
            y: (this.touchCurrent[0].y + this.touchCurrent[1].y) / 2,
            timestamp: Date.now(),
        };

        this.onPinch({
            scale,
            center,
            distance: currentDistance,
        });
    }

    private handleTapGesture(point: TouchPoint): void {
        const isDoubleTap = this.checkDoubleTap(point);

        if (isDoubleTap && this.onDoubleTap) {
            // Clear single tap timeout if double tap detected
            if (this.doubleTapTimeout) {
                clearTimeout(this.doubleTapTimeout);
                this.doubleTapTimeout = null;
            }

            this.onDoubleTap({
                x: point.x,
                y: point.y,
                timestamp: point.timestamp,
                isDoubleTap: true,
            });
        } else if (this.onTap) {
            // Delay single tap to check for double tap
            this.doubleTapTimeout = setTimeout(() => {
                this.onTap!({
                    x: point.x,
                    y: point.y,
                    timestamp: point.timestamp,
                    isDoubleTap: false,
                });
                this.doubleTapTimeout = null;
            }, this.config.doubleTapDelay);
        }

        this.lastTap = point;
    }

    private checkDoubleTap(point: TouchPoint): boolean {
        if (!this.lastTap) return false;

        const timeDiff = point.timestamp - this.lastTap.timestamp;
        const distance = this.calculateDistance(point, this.lastTap);

        return timeDiff <= this.config.doubleTapDelay && distance <= this.config.doubleTapDistance;
    }

    private calculateDistance(point1: TouchPoint, point2: TouchPoint): number {
        const deltaX = point2.x - point1.x;
        const deltaY = point2.y - point1.y;
        return Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    }

    // Public API
    public setSwipeHandler(callback: GestureCallback<SwipeGesture>): void {
        this.onSwipe = callback;
    }

    public setPinchHandler(callback: GestureCallback<PinchGesture>): void {
        this.onPinch = callback;
    }

    public setTapHandler(callback: GestureCallback<TapGesture>): void {
        this.onTap = callback;
    }

    public setDoubleTapHandler(callback: GestureCallback<TapGesture>): void {
        this.onDoubleTap = callback;
    }

    public destroy(): void {
        this.element.removeEventListener('touchstart', this.handleTouchStart.bind(this));
        this.element.removeEventListener('touchmove', this.handleTouchMove.bind(this));
        this.element.removeEventListener('touchend', this.handleTouchEnd.bind(this));
        this.element.removeEventListener('touchcancel', this.handleTouchCancel.bind(this));

        if (this.doubleTapTimeout) {
            clearTimeout(this.doubleTapTimeout);
        }
    }
}

// React hook for touch gestures
export interface UseTouchGesturesOptions {
    onSwipe?: GestureCallback<SwipeGesture>;
    onPinch?: GestureCallback<PinchGesture>;
    onTap?: GestureCallback<TapGesture>;
    onDoubleTap?: GestureCallback<TapGesture>;
    config?: Partial<TouchGestureRecognizer['config']>;
}

export const useTouchGestures = <T extends HTMLElement>(
    options: UseTouchGesturesOptions = {}
) => {
    const elementRef = useRef<T>(null);
    const recognizerRef = useRef<TouchGestureRecognizer | null>(null);

    useEffect(() => {
        if (!elementRef.current) return;

        recognizerRef.current = new TouchGestureRecognizer(elementRef.current, options.config);

        if (options.onSwipe) {
            recognizerRef.current.setSwipeHandler(options.onSwipe);
        }

        if (options.onPinch) {
            recognizerRef.current.setPinchHandler(options.onPinch);
        }

        if (options.onTap) {
            recognizerRef.current.setTapHandler(options.onTap);
        }

        if (options.onDoubleTap) {
            recognizerRef.current.setDoubleTapHandler(options.onDoubleTap);
        }

        return () => {
            recognizerRef.current?.destroy();
        };
    }, [options.onSwipe, options.onPinch, options.onTap, options.onDoubleTap]);

    return elementRef;
};

// Mobile-specific utilities
export class MobileUtils {
    static isMobile(): boolean {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    static isTablet(): boolean {
        return /iPad|Android(?!.*Mobile)/i.test(navigator.userAgent);
    }

    static isTouchDevice(): boolean {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    }

    static getViewportSize(): { width: number; height: number } {
        return {
            width: Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0),
            height: Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0),
        };
    }

    static getOrientation(): 'portrait' | 'landscape' {
        const { width, height } = this.getViewportSize();
        return width > height ? 'landscape' : 'portrait';
    }

    static preventZoom(): void {
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });

        document.addEventListener('gesturestart', (e) => {
            e.preventDefault();
        });
    }

    static enableSmoothScrolling(): void {
        document.documentElement.style.scrollBehavior = 'smooth';
        document.body.style.scrollBehavior = 'smooth';
    }

    static optimizeForMobile(): void {
        // Add viewport meta tag if not present
        if (!document.querySelector('meta[name="viewport"]')) {
            const viewport = document.createElement('meta');
            viewport.name = 'viewport';
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
            document.head.appendChild(viewport);
        }

        // Prevent zoom
        this.preventZoom();

        // Enable smooth scrolling
        this.enableSmoothScrolling();

        // Add mobile-specific CSS classes
        document.body.classList.add(
            this.isMobile() ? 'mobile' : 'desktop',
            this.isTablet() ? 'tablet' : 'not-tablet',
            this.isTouchDevice() ? 'touch' : 'no-touch'
        );
    }
}

// Swipe navigation component
export interface SwipeNavigationProps {
    onSwipeLeft?: () => void;
    onSwipeRight?: () => void;
    onSwipeUp?: () => void;
    onSwipeDown?: () => void;
    children: React.ReactNode;
    className?: string;
}

export const SwipeNavigation: React.FC<SwipeNavigationProps> = ({
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown,
    children,
    className = '',
}) => {
    const elementRef = useTouchGestures<HTMLDivElement>({
        onSwipe: (gesture) => {
            switch (gesture.direction) {
                case 'left':
                    onSwipeLeft?.();
                    break;
                case 'right':
                    onSwipeRight?.();
                    break;
                case 'up':
                    onSwipeUp?.();
                    break;
                case 'down':
                    onSwipeDown?.();
                    break;
            }
        },
    });

    return (
        <div ref= { elementRef } className = { className } >
            { children }
            </div>
  );
};

// Pull to refresh component
export interface PullToRefreshProps {
    onRefresh: () => Promise<void>;
    children: React.ReactNode;
    threshold?: number;
    className?: string;
}

export const PullToRefresh: React.FC<PullToRefreshProps> = ({
    onRefresh,
    children,
    threshold = 100,
    className = '',
}) => {
    const [isRefreshing, setIsRefreshing] = React.useState(false);
    const [pullDistance, setPullDistance] = React.useState(0);
    const startY = React.useRef(0);

    const elementRef = useTouchGestures<HTMLDivElement>({
        onSwipe: async (gesture) => {
            if (gesture.direction === 'down' && gesture.distance > threshold && window.scrollY === 0) {
                setIsRefreshing(true);
                try {
                    await onRefresh();
                } finally {
                    setIsRefreshing(false);
                    setPullDistance(0);
                }
            }
        },
    });

    React.useEffect(() => {
        const element = elementRef.current;
        if (!element) return;

        const handleTouchStart = (e: TouchEvent) => {
            if (window.scrollY === 0) {
                startY.current = e.touches[0].clientY;
            }
        };

        const handleTouchMove = (e: TouchEvent) => {
            if (window.scrollY === 0 && !isRefreshing) {
                const currentY = e.touches[0].clientY;
                const distance = Math.max(0, currentY - startY.current);
                setPullDistance(Math.min(distance, threshold * 1.5));
            }
        };

        const handleTouchEnd = () => {
            if (pullDistance < threshold) {
                setPullDistance(0);
            }
        };

        element.addEventListener('touchstart', handleTouchStart, { passive: true });
        element.addEventListener('touchmove', handleTouchMove, { passive: true });
        element.addEventListener('touchend', handleTouchEnd, { passive: true });

        return () => {
            element.removeEventListener('touchstart', handleTouchStart);
            element.removeEventListener('touchmove', handleTouchMove);
            element.removeEventListener('touchend', handleTouchEnd);
        };
    }, [pullDistance, threshold, isRefreshing]);

    return (
        <div ref={elementRef} className={className}>
            {pullDistance > 0 && (
                <div
                    className="flex items-center justify-center py-4 text-gray-600"
                    style={{ transform: `translateY(${Math.min(pullDistance, threshold)}px)` }}
                >
                    {isRefreshing ? (
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    ) : pullDistance > threshold ? (
                        <span>Release to refresh</span>
                    ) : (
                        <span>Pull to refresh</span>
                    )}
                </div>
            )}
            <div style={{ transform: `translateY(${Math.min(pullDistance, threshold)}px)` }}>
                {children}
            </div>
        </div>
    );
};