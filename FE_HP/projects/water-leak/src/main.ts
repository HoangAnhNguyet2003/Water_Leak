import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';

import { AppModule } from './app/app.module';

try {
  const _addEventListener = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function(type: string, listener: EventListenerOrEventListenerObject, options?: any) {
    try {
      if (type === 'touchstart' || type === 'touchmove' || type === 'wheel') {

        const el = this as any;
        if (el && el.classList && (el.classList.contains('apexcharts-canvas') || el.classList.contains('apexcharts-svg') || el.classList.contains('apexcharts-inner')) ) {
          if (typeof options === 'object') {
            options = Object.assign({}, options, { passive: false });
          } else if (options === undefined) {
            options = { passive: false };
          }
        }
      }
    } catch (e) {
    }
    return _addEventListener.call(this, type, listener, options);
  };
} catch (e) {
}

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
