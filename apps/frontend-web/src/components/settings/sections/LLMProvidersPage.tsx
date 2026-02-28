import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ShieldCheck } from 'lucide-react';
import { AnthropicIcon } from '../../icons/AnthropicIcon';
import { OllamaIcon } from '../../icons/OllamaIcon';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../../ui/collapsible';
import { SettingsSection } from '../SettingsSection';
import { LocalLLMSettings } from './LocalLLMSettings';
import { LLMAccountsSettings } from './LLMAccountsSettings';
import { QALLMProviderSettings } from './QALLMProviderSettings';
import type { AppSettings } from '../../../shared/types/settings';

interface LLMProvidersPageProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  isOpen: boolean;
}

interface PanelProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Panel({ icon, title, description, defaultOpen = false, children }: PanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="rounded-lg border border-border overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-muted/50 transition-colors">
            <div className="flex items-center gap-3">
              <div className="text-muted-foreground">{icon}</div>
              <div>
                <h4 className="text-sm font-semibold text-foreground">{title}</h4>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
            </div>
            <ChevronDown className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t border-border px-4 py-4">
            {children}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

export function LLMProvidersPage({ settings, onSettingsChange, isOpen }: LLMProvidersPageProps) {
  const { t } = useTranslation('settings');

  return (
    <SettingsSection
      title={t('sections.llmProvider.title')}
      description={t('sections.llmProvider.description')}
    >
      <div className="space-y-3">
        <Panel
          icon={<AnthropicIcon className="h-4 w-4" />}
          title={t('sections.llmProvider.accounts.title')}
          description={t('sections.llmProvider.accounts.description')}
          defaultOpen
        >
          <LLMAccountsSettings isOpen={isOpen} />
        </Panel>

        <Panel
          icon={<OllamaIcon className="h-4 w-4" />}
          title={t('sections.llmProvider.localLlms.title')}
          description={t('sections.llmProvider.localLlms.description')}
        >
          <LocalLLMSettings settings={settings} onSettingsChange={onSettingsChange} />
        </Panel>

        <Panel
          icon={<ShieldCheck className="h-4 w-4" />}
          title={t('sections.llmProvider.qaProvider.title')}
          description={t('sections.llmProvider.qaProvider.description')}
        >
          <QALLMProviderSettings settings={settings} onSettingsChange={onSettingsChange} />
        </Panel>
      </div>
    </SettingsSection>
  );
}
