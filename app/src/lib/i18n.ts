import { cookies } from 'next/headers';
import enTranslations from '../i18n/en.json';
import ruTranslations from '../i18n/ru.json';

export type Locale = 'en' | 'ru';

const translations = {
  en: enTranslations,
  ru: ruTranslations,
};

export function getLocale(): Locale {
  try {
    const cookieStore = cookies();
    const locale = cookieStore.get('locale')?.value as Locale;
    return locale && (locale === 'en' || locale === 'ru') ? locale : 'ru';
  } catch {
    return 'ru';
  }
}

export function getTranslations(locale?: Locale) {
  const currentLocale = locale || getLocale();
  return translations[currentLocale];
}

export function t(key: string, locale?: Locale): string {
  const trans = getTranslations(locale);
  const keys = key.split('.');
  let value: any = trans;
  
  for (const k of keys) {
    value = value?.[k];
  }
  
  return typeof value === 'string' ? value : key;
}

// Client-side hook
export function useTranslations() {
  if (typeof window !== 'undefined') {
    const locale = localStorage.getItem('locale') as Locale || 'ru';
    return {
      t: (key: string) => t(key, locale),
      locale,
      setLocale: (newLocale: Locale) => {
        localStorage.setItem('locale', newLocale);
        document.cookie = `locale=${newLocale}; path=/; max-age=31536000`;
        window.location.reload();
      }
    };
  }
  
  return {
    t: (key: string) => t(key, 'ru'),
    locale: 'ru' as Locale,
    setLocale: () => {}
  };
}