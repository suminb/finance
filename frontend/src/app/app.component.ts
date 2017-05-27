import { Component } from '@angular/core';

import { DartService } from './dart.service';

@Component({
    selector: 'app-root',
    template: `
    <a [routerLink]="['/dart']">View DART reports</a>
    <router-outlet></router-outlet>
    `,
    providers: [DartService]
})
export class AppComponent {
}
