import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpModule } from '@angular/http';
import { RouterModule } from '@angular/router';

import { AppComponent } from './app.component';
import { ListDartComponent } from './listdart.component';
import { ViewDartComponent } from './viewdart.component';
import { DartService } from './dart.service';

@NgModule({
    imports: [
        BrowserModule,
        FormsModule,
        HttpModule,
        RouterModule.forRoot([
            {
                path: 'dart',
                component: ListDartComponent
            },
            {
                path: 'dart/:id',
                component: ViewDartComponent
            }
        ])
    ],
    declarations: [
        AppComponent,
        ListDartComponent,
        ViewDartComponent,
    ],
    providers: [
        DartService
    ],
    bootstrap: [AppComponent]
})


export class AppModule {
}
