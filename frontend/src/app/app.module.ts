import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpModule } from '@angular/http';
import { RouterModule } from '@angular/router';

import { AppComponent } from './app.component';
import { DartListComponent } from './dart-list.component';
import { DartViewComponent } from './dart-view.component';
import { DartService } from './dart.service';

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
            }
        ])
    ],
    declarations: [
        AppComponent,
        DartListComponent,
        DartViewComponent,
    ],
    providers: [
        DartService
    ],
    bootstrap: [AppComponent]
})


export class AppModule {
}
