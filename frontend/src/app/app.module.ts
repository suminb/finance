import { NgModule }       from '@angular/core';
import { BrowserModule }  from '@angular/platform-browser';
import { FormsModule }    from '@angular/forms';
import { HttpModule } from '@angular/http';
import { RouterModule } from '@angular/router';

import { AppComponent }        from './app.component';
import { ListDartComponent }     from './listdart.component';
import { DartService }         from './dart.service';

@NgModule({
  imports: [
    BrowserModule,
    FormsModule,
    HttpModule,
    RouterModule.forRoot([
      {
        path: 'listdart',
        component: ListDartComponent
      }
    ])
  ],
  declarations: [
    AppComponent,
    ListDartComponent,
  ],
  providers: [
    DartService
  ],
  bootstrap: [ AppComponent ]
})


export class AppModule {
}
