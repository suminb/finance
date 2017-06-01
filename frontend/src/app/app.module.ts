import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpModule } from '@angular/http';
import { RouterModule } from '@angular/router';

import { AppComponent } from './app.component';
import { DartListComponent } from './dart-list.component';
import { DartViewComponent } from './dart-view.component';
import { DartService } from './dart.service';
import { PortfolioListComponent } from './portfolio-list.component';
import { PortfolioViewComponent } from './portfolio-view.component';
import { PortfolioService } from './portfolio.service';

@NgModule({
    imports: [
        BrowserModule,
        FormsModule,
        HttpModule,
        RouterModule.forRoot([
            {
                path: 'dart',
                component: DartListComponent
            },
            {
                path: 'dart/:id',
                component: DartViewComponent
            },
            {
                path: 'portfolio',
                component: PortfolioListComponent
            },
            {
                path: 'portfolio/:id',
                component: PortfolioViewComponent
            }
        ])
    ],
    declarations: [
        AppComponent,
        DartListComponent,
        DartViewComponent,
        PortfolioListComponent,
        PortfolioViewComponent,
    ],
    providers: [
        DartService,
        PortfolioService
    ],
    bootstrap: [AppComponent]
})


export class AppModule {
}
