import { useTranslation } from 'react-i18next';
import { Separator } from '../../ui/separator';
import { SettingsSection } from '../SettingsSection';
import { LocalLLMSettings } from './LocalLLMSettings';
import { LLMAccountsSettings } from './LLMAccountsSettings';
import type { AppSettings } from '../../../shared/types/settings';

interface LLMProvidersPageProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  isOpen: boolean;
}

export function LLMProvidersPage({ settings, onSettingsChange, isOpen }: LLMProvidersPageProps) {
  const { t } = useTranslation('settings');

  return (
    <SettingsSection
      title={t('sections.llmProvider.title')}
      description={t('sections.llmProvider.description')}
    >
      <LocalLLMSettings settings={settings} onSettingsChange={onSettingsChange} />
      <Separator />
      <LLMAccountsSettings isOpen={isOpen} />
    </SettingsSection>
  );
}
