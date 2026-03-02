import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Check,
  AlertTriangle,
  X,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { Button } from './ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from './ui/popover';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from './ui/tooltip';
import { cn } from '../lib/utils';
import { StatusBadgeButton } from './ui/StatusBadgeButton';
import { OllamaIcon } from './icons/OllamaIcon';
import { apiRequest } from '../lib/api-client';

interface LocalLLMStatusBadgeProps {
  className?: string;
  iconOnly?: boolean;
}

interface LLMProvider {
  id: string;
  name: string;
  url: string;
  detected: boolean;
  installed: boolean;
  running: boolean;
  version: string;
  modelCount: number;
  models: string[];
}

// Refresh every 5 minutes
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Local LLM status badge for the header.
 * Shows Ollama (local LLM) status with icon, colored status dot,
 * and rich popover modal with version info, model list, and quick actions.
 * Follows the same icon + status dot + Tooltip + Popover pattern as CLIToolStatusBadge.
 */
export function LocalLLMStatusBadge({ className, iconOnly = false }: LocalLLMStatusBadgeProps) {
  const { t } = useTranslation(['navigation', 'common']);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [ollamaProvider, setOllamaProvider] = useState<LLMProvider | null>(null);

  const detect = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true);
    try {
      const result = await apiRequest<{ providers: LLMProvider[] }>('/settings/local-llm/detect');
      if (result.success && result.data) {
        const ollama = result.data.providers.find((p) => p.id === 'ollama') ?? null;
        setOllamaProvider(ollama);
        setLastChecked(new Date());
      }
    } catch (err) {
      // Silently handle — local LLM is optional
    } finally {
      setIsLoading(false);
      if (showRefreshing) setIsRefreshing(false);
    }
  }, []);

  // Initial detection + periodic refresh
  useEffect(() => {
    detect();
    const interval = setInterval(() => detect(), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [detect]);

  const handleRefresh = () => detect(true);

  // Derive status from provider data
  const installed = ollamaProvider?.installed ?? false;
  const running = ollamaProvider?.running ?? false;

  const statusType = running ? 'running' : installed ? 'installed' : 'not-installed';

  const dotColor =
    statusType === 'running' ? 'bg-green-500' :
    statusType === 'installed' ? 'bg-yellow-500' :
    'bg-muted-foreground/40';

  const tooltipText = (() => {
    switch (statusType) {
      case 'running':
        return `Ollama — ${t('navigation:localLLM.running')}`;
      case 'installed':
        return `Ollama — ${t('navigation:localLLM.notRunning')}`;
      default:
        return `Ollama — ${t('navigation:localLLM.notInstalled')}`;
    }
  })();

  // Status icon inside popover header
  const statusIcon = (() => {
    if (!installed) return <X className="h-3 w-3" />;
    if (!running) return <AlertTriangle className="h-3 w-3" />;
    return <Check className="h-3 w-3" />;
  })();

  // Status text inside popover header
  const statusText = (() => {
    if (!installed) return t('navigation:localLLM.notInstalled');
    if (!running) return t('navigation:localLLM.notRunning');
    return t('navigation:localLLM.running');
  })();

  if (isLoading) return null;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <StatusBadgeButton
              iconOnly={iconOnly}
              icon={<OllamaIcon className="h-4 w-4" />}
              label="Ollama"
              dotColor={dotColor}
              className={cn(
                statusType === 'not-installed' && 'opacity-50',
                statusType === 'installed' && 'text-yellow-600 dark:text-yellow-500',
                className,
              )}
            />
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent side={iconOnly ? 'bottom' : 'right'}>
          {tooltipText}
        </TooltipContent>
      </Tooltip>

      <PopoverContent side={iconOnly ? 'bottom' : 'right'} align="end" className="w-72">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10">
              <OllamaIcon className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h4 className="text-sm font-medium">Ollama</h4>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {statusIcon}
                {statusText}
              </p>
            </div>
          </div>

          {/* Version and model info */}
          {installed && (
            <div className="text-xs space-y-1 p-2 bg-muted rounded-md">
              {ollamaProvider?.version && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t('navigation:localLLM.version')}:</span>
                  <span className="font-mono">{ollamaProvider.version}</span>
                </div>
              )}
              {running && ollamaProvider?.modelCount !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t('navigation:localLLM.models')}:</span>
                  <span>{ollamaProvider.modelCount}</span>
                </div>
              )}
              {lastChecked && (
                <div className="flex justify-between text-muted-foreground">
                  <span>{t('navigation:localLLM.lastChecked')}:</span>
                  <span>{lastChecked.toLocaleTimeString()}</span>
                </div>
              )}
            </div>
          )}

          {/* Model list */}
          {running && ollamaProvider?.models && ollamaProvider.models.length > 0 && (
            <div className="text-xs space-y-1">
              <span className="text-muted-foreground font-medium">{t('navigation:localLLM.availableModels')}:</span>
              <ul className="mt-1 space-y-0.5 max-h-28 overflow-y-auto">
                {ollamaProvider.models.slice(0, 8).map((model) => (
                  <li key={model} className="font-mono text-xs px-2 py-0.5 rounded bg-muted">
                    {model}
                  </li>
                ))}
                {ollamaProvider.models.length > 8 && (
                  <li className="text-muted-foreground px-2">
                    +{ollamaProvider.models.length - 8} {t('navigation:localLLM.more')}
                  </li>
                )}
              </ul>
            </div>
          )}

          {/* Status callout when not running */}
          {installed && !running && (
            <div className="text-xs p-2 rounded-md flex items-start gap-2 bg-yellow-500/10 text-yellow-700 dark:text-yellow-400">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{t('navigation:localLLM.startHint')}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={cn('h-3 w-3', isRefreshing && 'animate-spin')} />
              {t('common:refresh', 'Refresh')}
            </Button>
            {!installed && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1 flex-1"
                onClick={() => window.open('https://ollama.com', '_blank')}
              >
                <ExternalLink className="h-3 w-3" />
                {t('navigation:localLLM.install')}
              </Button>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
